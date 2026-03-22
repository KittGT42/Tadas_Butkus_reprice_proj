import schedule
import time
import subprocess
import os
from datetime import datetime
import json
from filelock import FileLock
import logging
from typing import Optional, Dict
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_adjuster.log'),
        logging.StreamHandler()
    ]
)


class PriceAdjuster:
    def __init__(self):
        self.lock_file = "download.lock"
        self.adjustments_file = "daily_adjustments.json"
        self.max_daily_adjustments = 5
        self.lock_timeout = 3600
        self._daily_adjustments_cache = {}
        self._last_cache_update = None
        self._adjustment_lock = asyncio.Lock()
        self._initialize_adjustments_file()

    def _initialize_adjustments_file(self):
        """Initialize adjustments file with empty structure if it doesn't exist or is empty"""
        try:
            if not os.path.exists(self.adjustments_file) or os.path.getsize(self.adjustments_file) == 0:
                today = datetime.now().strftime('%Y-%m-%d')
                initial_data = {today: {}}

                with open(self.adjustments_file, 'w') as f:
                    json.dump(initial_data, f)

                self._daily_adjustments_cache = initial_data
                self._last_cache_update = datetime.now()

                logging.info(f"Initialized empty adjustments file with date {today}")
        except Exception as e:
            logging.error(f"Error initializing adjustments file: {e}")
            # Create minimal valid structure
            with open(self.adjustments_file, 'w') as f:
                json.dump({}, f)

    def _get_composite_key(self, barcode: str, country: str) -> str:
        """Create a composite key from barcode and country"""
        return f"{barcode}-{country}"

    def _is_download_in_progress(self) -> bool:
        """Check if download is currently in progress"""
        if not os.path.exists(self.lock_file):
            return False

        creation_time = os.path.getctime(self.lock_file)
        if (time.time() - creation_time) > self.lock_timeout:
            logging.warning("Detected stale lock. Removing...")
            self._remove_lock()
            return False
        return True

    def _create_lock(self):
        """Create a lock file"""
        with open(self.lock_file, 'w') as f:
            f.write(str(datetime.now()))

    def _remove_lock(self):
        """Remove the lock file if it exists"""
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    async def _get_daily_adjustments(self) -> tuple[dict, str]:
        today = datetime.now().strftime('%Y-%m-%d')

        if (self._last_cache_update and
                self._last_cache_update.strftime('%Y-%m-%d') == today):
            return self._daily_adjustments_cache, today

        try:
            if os.path.exists(self.adjustments_file):
                with open(self.adjustments_file, 'r') as f:
                    adjustments = json.load(f)
            else:
                adjustments = {}

            # Clean old records and initialize today if needed
            if today not in adjustments:
                adjustments = {today: {}}

            # Update cache
            self._daily_adjustments_cache = adjustments
            self._last_cache_update = datetime.now()

            return adjustments, today
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error reading adjustments file: {e}")
            # Return empty structure if there's an error
            return {today: {}}, today

    async def get_adjustment_stats(self) -> Optional[Dict[str, int]]:
        """Returns today's adjustment statistics with country information"""
        try:
            adjustments, today = await self._get_daily_adjustments()
            stats = {}

            # Group by country
            for composite_key, count in adjustments[today].items():
                if '-' in composite_key:
                    country = composite_key.split('-')[1]
                    stats[country] = stats.get(country, 0) + 1

            return {
                'total_products': len(adjustments[today]),
                'total_adjustments': sum(adjustments[today].values()),
                'adjustments_by_country': stats
            }
        except Exception as e:
            logging.error(f"Error getting statistics: {e}")
            return None

    async def update_adjustment_count(self, barcode: str, country: str) -> bool:
        """Thread-safe update of adjustment counts with country tracking"""
        async with self._adjustment_lock:
            try:
                adjustments, today = await self._get_daily_adjustments()
                composite_key = self._get_composite_key(barcode, country)

                if composite_key not in adjustments[today]:
                    adjustments[today][composite_key] = 1
                else:
                    adjustments[today][composite_key] += 1

                with FileLock(f"{self.adjustments_file}.lock"):
                    with open(self.adjustments_file, 'w') as f:
                        json.dump(adjustments, f)
                return True
            except Exception as e:
                logging.error(f"Error updating adjustment counter: {e}")
                return False

    async def can_adjust_price(self, barcode: str, country: str) -> bool:
        """Check if price adjustment is allowed using cached data with country tracking"""
        try:
            adjustments, today = await self._get_daily_adjustments()
            composite_key = self._get_composite_key(barcode, country)
            return adjustments[today].get(composite_key, 0) < self.max_daily_adjustments
        except Exception as e:
            logging.error(f"Error checking adjustment possibility: {e}")
            return False

    async def download_prices(self) -> bool:
        """Asynchronous price download"""
        if self._is_download_in_progress():
            logging.warning("Active lock detected. Skipping download.")
            return False

        try:
            self._create_lock()
            logging.info("Starting price download")

            process = await asyncio.create_subprocess_exec(
                'python', 'download_all_products_buy_box_price.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.lock_timeout)
                if process.returncode == 0:
                    logging.info("Price download completed successfully")
                    if stderr:
                        logging.warning(f"Download stderr: {stderr.decode()}")
                    return True
                else:
                    logging.error(f"Price download failed with code {process.returncode}")
                    if stderr:
                        logging.error(f"Download stderr: {stderr.decode()}")
                    return False
            except asyncio.TimeoutError:
                process.kill()
                logging.error("Download timeout exceeded")
                return False

        except Exception as e:
            logging.error(f"Error during price download: {e}")
            return False
        finally:
            self._remove_lock()

    async def adjust_prices(self) -> bool:
        """Asynchronous price adjustment"""
        if self._is_download_in_progress():
            logging.info("Price download in progress, skipping price adjustment")
            return False

        try:
            logging.info("Starting price adjustment")

            process = await asyncio.create_subprocess_exec(
                'python', 'main.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.lock_timeout)
                if process.returncode == 0:
                    logging.info("Price adjustment completed successfully")
                    if stderr:
                        logging.warning(f"Adjustment stderr: {stderr.decode()}")

                    # Display statistics after successful adjustment
                    if stats := await self.get_adjustment_stats():
                        logging.info(f"Today's adjustment statistics:")
                        logging.info(f"Total products processed: {stats['total_products']}")
                        logging.info(f"Total adjustments made: {stats['total_adjustments']}")
                        logging.info("Adjustments by country:")
                        for country, count in stats['adjustments_by_country'].items():
                            logging.info(f"  {country}: {count}")

                    return True
                else:
                    logging.error(f"Price adjustment failed with code {process.returncode}")
                    if stderr:
                        logging.error(f"Adjustment stderr: {stderr.decode()}")
                    return False
            except asyncio.TimeoutError:
                process.kill()
                logging.error("Price adjustment timeout exceeded")
                return False

        except Exception as e:
            logging.error(f"Error during price adjustment: {e}")
            return False


async def scheduled_task(adjuster: PriceAdjuster):
    """Asynchronous scheduled task execution"""
    if await adjuster.download_prices():
        await asyncio.sleep(30)  # Wait 30 seconds after download
        await adjuster.adjust_prices()


async def main():
    adjuster = PriceAdjuster()

    # Initial run
    await scheduled_task(adjuster)

    while True:
        try:
            # Run every hour
            await asyncio.sleep(7200)  # 2 hour
            await scheduled_task(adjuster)
        except Exception as e:
            logging.error(f"Critical scheduler error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retry


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())