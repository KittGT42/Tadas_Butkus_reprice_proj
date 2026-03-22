# Price Optimization System
## Overview
This system helps you automatically manage and optimize product prices across different countries (Lithuania, Finland, Latvia, and Estonia). It monitors competitor prices and adjusts your prices to stay competitive while maintaining profit margins.

## What Does It Do?
- Automatically downloads current market prices
- Checks competitor prices every 2 hours
- Adjusts your prices when needed
- Maintains your profit margins
- Works in multiple countries
- Prevents too many price changes for one product
- Keeps track of all price changes

## System Requirements
- Python 3.8 or newer
- Google Sheets access
- Internet connection
- Pigu Group API access

## Setup Instructions

### 1. Install Required Software
- Install Python from [python.org](https://python.org)
- Install required Python packages:
  ```
  pip install google-oauth2-client
  pip install google-api-python-client
  pip install requests
  pip install python-dotenv
  pip install schedule
  pip install filelock
  ```
- Or install poetry and run `poetry install` in terminal

### 2. Configure Access
1. Place your Google Sheets API credentials file (`sales-ai-manager-animals-tems-16214ffd1364.json`) in the main folder
2. Create a `.env` file with your Pigu API token:
   ```
   PIGU_TOKEN=your_token_here
   ```

### 3. Configure Settings
The system uses these files for configuration:
- `main_opt.py`: Contains main price adjustment logic
- `scheduler.py`: Controls how often prices are checked
- `work_with_sheet.py`: Contains Google Sheet settings

#### Important Customization Locations

1. **Modifying Countries**
   - File: `main.py`
   - Line 9: Look for the comment "Countries to process"
   ```python
   # Countries to process (LT - Lithuania, FI - Finland, LV - Latvia, EE - Estonia)
   countries = ['LT', 'FI', 'LV', 'EE']
   ```
   - To add or remove countries, simply modify this list
   - Make sure to use the correct country codes:
     * LT - Lithuania
     * FI - Finland
     * LV - Latvia
     * EE - Estonia

2. **Adding Barcodes to Ignore List**
   - File: `main.py`
   - Line 11: Look for the variable `barcodes_what_need_to_skip`
   ```python
   barcodes_what_need_to_skip = ['4356348953478598', '123981209381283018', '1283718293718293798']
   ```
   - To add new barcodes to ignore:
     * Open `main.py`
     * Find the `barcodes_what_need_to_skip` list
     * Add new barcode numbers inside quotes and separate with commas
     * Example of adding new barcode:
     ```python
     barcodes_what_need_to_skip = ['4356348953478598', '123981209381283018', '1283718293718293798', 'your_new_barcode_here']
     ```

Key settings you might want to change:
1. In `scheduler.py`:
   - `max_daily_adjustments = 5` (maximum price changes per product per day)
   - Schedule timing (currently set to every 1 minute)

2. In `main.py`:
   - VAT rates for each country
   - Price rounding rules
   - Maximum price reduction limits

### 4. Google Sheet Structure
Your Google Sheet should have these columns (in this order):
- Barcode
- Skip product flag
- Product amount
- Country-specific columns for:
  - Price
  - Stock price
  - Best price
  - Carriage rate
  - Transportation costs
  - VAT calculations
  - Profit margins

## How to Run
1. Start the main system:
   ```
   python scheduler.py
   ```
2. The system will:
   - Download current market prices
   - Check for needed price adjustments
   - Make changes if needed
   - Repeat this process every minute

## Important Notes
- The system won't make more than 5 price changes per product per day
- It skips products marked with specific barcodes (listed in code)
- It only changes prices within safe limits to protect your profits
- All activities are logged in `price_adjuster.log`

## Safety Features
- Prevents too many price changes
- Ensures minimum profit margins
- Has maximum price reduction limits
- Locks prevent multiple processes running at once
- Logs all actions for review

## Troubleshooting
If you encounter issues:
1. Check `price_adjuster.log` for error messages
2. Verify your internet connection
3. Confirm Google Sheets API access
4. Verify Pigu API token is valid
5. Make sure all required Python packages are installed

## Support
Telegram: @kittgt
Gmail: zabutniy10@gmail.com
Skype: neoyura
Remember to regularly check the `price_adjuster.log` file to monitor system activity and catch any potential issues early.