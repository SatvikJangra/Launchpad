import requests
import json
import pandas as pd
import datetime
import time
import os

def color_text(text, color_code):
    """Apply ANSI color codes to the given text."""
    return f"\033[{color_code}m{text}\033[0m"

COLORS = {
    "red": "91", "green": "92", "yellow": "93", "light_purple": "94",
    "magenta": "95", "cyan": "96", "light_gray": "97", "black": "98", "bold": "1", "purple": "95"
}

def round_nearest(x, base=50):
    """Round the number to the nearest base."""
    return int(round(x / base) * base)

API_ENDPOINTS = {
    "oc": "https://www.nseindia.com/option-chain",
    "bnf": "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY",
    "nf": "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
    "indices": "https://www.nseindia.com/api/allIndices"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
    'Accept-Language': 'en,gu;q=0.9,hi;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br'
}

sess = requests.Session()
cookies = {}

def set_cookie():
    """Retrieve and set cookies for the session."""
    global cookies
    try:
        response = sess.get(API_ENDPOINTS['oc'], headers=HEADERS, timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        cookies = dict(response.cookies)
    except requests.RequestException as e:
        print(f"Error setting cookies: {e}")

def get_data(url, retries=3, delay=1):
    """Retrieve data from the given URL with retry mechanism."""
    set_cookie()
    for attempt in range(retries):
        try:
            response = sess.get(url, headers=HEADERS, timeout=5, cookies=cookies)
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.status_code == 200:
                return response.text
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            time.sleep(delay)
    return None

def highest_oi(option_type, num, step, nearest, url):
    """Find the strike price with the highest open interest for the given option type."""
    strike = nearest - (step * num)
    start_strike = strike
    response_text = get_data(url)
    if response_text:
        data = json.loads(response_text)
        curr_expiry_date = data["records"]["expiryDates"][0]
        max_oi = 0
        max_oi_strike = 0

        for item in data['records']['data']:
            if item["expiryDate"] == curr_expiry_date:
                if start_strike <= item["strikePrice"] < start_strike + (step * num * 2):
                    oi = item[option_type]["openInterest"]
                    if oi > max_oi:
                        max_oi = oi
                        max_oi_strike = item["strikePrice"]

        return max_oi_strike
    else:
        print("Failed to retrieve data.")
        return None

def set_header():
    """Set the header information for Nifty and Bank Nifty."""
    global bnf_ul, nf_ul, bnf_nearest, nf_nearest
    response_text = get_data(API_ENDPOINTS['indices'])
    if response_text:
        data = json.loads(response_text)
        print(data)

        for index in data["data"]:
            if index["index"] == "NIFTY 50":
                nf_ul = index["last"]
                print("Nifty")
            if index["index"] == "NIFTY BANK":
                bnf_ul = index["last"]
                print("Bank Nifty")

        bnf_nearest = round_nearest(bnf_ul, 100)
        nf_nearest = round_nearest(nf_ul, 50)
    else:
        print("Failed to retrieve index data.")

def print_header(index, ul, nearest):
    """Print header information for an index."""
    print(color_text(index.ljust(12, " ") + "=> ", COLORS["purple"]) +
          color_text(" Last Price: ", COLORS["light_purple"]) +
          color_text(str(ul), COLORS["bold"]) +
          color_text(" Nearest Strike: ", COLORS["light_purple"]) +
          color_text(str(nearest), COLORS["bold"]))

def print_hr():
    """Print a horizontal rule."""
    print(color_text("|".rjust(70, "-"), COLORS["yellow"]))

def print_oi(num, step, nearest, url, index_name, ul_value):
    """Print the open interest for options and return a DataFrame."""
    response_text = get_data(url)
    if response_text:
        data = json.loads(response_text)

        curr_expiry_date = data["records"]["expiryDates"][0]
        timestamp = datetime.datetime.now()

        # Define the columns to print
        columns_to_print = [
            "C_OI", "C_C_OI", "C_TTV", "C_IV", "C_LASTPRICE", "C_CHANGE", "C_BIDQTY", "C_BIDPRICE",
            "C_ASKQTY", "C_ASKPRICE", "STRIKEPRICE", "P_OI", "P_C_OI", "P_TTV", "P_IV",
            "P_LASTPRICE", "P_CHANGE", "P_BIDQTY", "P_BIDPRICE", "P_ASKQTY", "P_ASKPRICE"
        ]

        # Initialize a list to store rows of data
        data_rows = []

        # Print column headers in green
        header = "|".join(color_text(f"{col}".ljust(15), COLORS["green"]) if "STRIKEPRICE" in col
                          else color_text(f"{col}".ljust(15), COLORS["purple"]) for col in columns_to_print)
        print(header)

        for item in data['records']['data']:
            if item["expiryDate"] == curr_expiry_date:
                ce_oi = round(item["CE"]["openInterest"], 2) if "CE" in item else "NA"
                ce_coi = round(item["CE"]["changeinOpenInterest"], 2) if "CE" in item else "NA"
                ce_volume = round(item["CE"]["totalTradedVolume"], 2) if "CE" in item else "NA"
                ce_iv = round(item["CE"]["impliedVolatility"], 2) if "CE" in item else "NA"
                ce_last_price = round(item["CE"]["lastPrice"], 2) if "CE" in item else "NA"
                ce_change = round(item["CE"]["change"], 2) if "CE" in item else "NA"
                ce_bid_qty = round(item["CE"]["bidQty"], 2) if "CE" in item else "NA"
                ce_bid_price = round(item["CE"]["bidprice"], 2) if "CE" in item else "NA"
                ce_ask_qty = round(item["CE"]["askQty"], 2) if "CE" in item else "NA"
                ce_ask_price = round(item["CE"]["askPrice"], 2) if "CE" in item else "NA"

                pe_oi = round(item["PE"]["openInterest"], 2) if "PE" in item else "NA"
                pe_coi = round(item["PE"]["changeinOpenInterest"], 2) if "PE" in item else "NA"
                pe_volume = round(item["PE"]["totalTradedVolume"], 2) if "PE" in item else "NA"
                pe_iv = round(item["PE"]["impliedVolatility"], 2) if "PE" in item else "NA"
                pe_last_price = round(item["PE"]["lastPrice"], 2) if "PE" in item else "NA"
                pe_change = round(item["PE"]["change"], 2) if "PE" in item else "NA"
                pe_bid_qty = round(item["PE"]["bidQty"], 2) if "PE" in item else "NA"
                pe_bid_price = round(item["PE"]["bidprice"], 2) if "PE" in item else "NA"
                pe_ask_qty = round(item["PE"]["askQty"], 2) if "PE" in item else "NA"
                pe_ask_price = round(item["PE"]["askPrice"], 2) if "PE" in item else "NA"

                # Append row data to the list
                data_row = [
                    ce_oi, ce_coi, ce_volume, ce_iv, ce_last_price, ce_change, ce_bid_qty,
                    ce_bid_price, ce_ask_qty, ce_ask_price, item["strikePrice"], pe_oi, pe_coi,
                    pe_volume, pe_iv, pe_last_price, pe_change, pe_bid_qty, pe_bid_price,
                    pe_ask_qty, pe_ask_price
                ]

                data_rows.append(data_row)

                # Determine the color for the "STRIKEPRICE" column
                strike_color = COLORS["yellow"] if item["strikePrice"] == nearest else COLORS["cyan"]

                # Determine the color for the entire row of the nearest strike
                row_color = COLORS["yellow"] if item["strikePrice"] == nearest else COLORS["light_gray"]

                # Print values for each column
                row_values = [
                    color_text(str(ce_oi).ljust(15), row_color),
                    color_text(str(ce_coi).ljust(15), row_color),
                    color_text(str(ce_volume).ljust(15), row_color),
                    color_text(str(ce_iv).ljust(15), row_color),
                    color_text(str(ce_last_price).ljust(15), row_color),
                    color_text(str(ce_change).ljust(15), row_color),
                    color_text(str(ce_bid_qty).ljust(15), row_color),
                    color_text(str(ce_bid_price).ljust(15), row_color),
                    color_text(str(ce_ask_qty).ljust(15), row_color),
                    color_text(str(ce_ask_price).ljust(15), row_color),
                    color_text(str(item["strikePrice"]).ljust(15), strike_color),
                    # Continue for put columns
                    color_text(str(pe_oi).ljust(15), row_color),
                    color_text(str(pe_coi).ljust(15), row_color),
                    color_text(str(pe_volume).ljust(15), row_color),
                    color_text(str(pe_iv).ljust(15), row_color),
                    color_text(str(pe_last_price).ljust(15), row_color),
                    color_text(str(pe_change).ljust(15), row_color),
                    color_text(str(pe_bid_qty).ljust(15), row_color),
                    color_text(str(pe_bid_price).ljust(15), row_color),
                    color_text(str(pe_ask_qty).ljust(15), row_color),
                    color_text(str(pe_ask_price).ljust(15), row_color),
                ]

                # Print the entire row with the specified color
                row = "|".join(str(val) for val in row_values)
                print(row)

        # Create a DataFrame with the collected data
        df = pd.DataFrame(data_rows, columns=columns_to_print)

        # Add additional columns for last price, expiry date, and timestamp
        df["LASTPRICE"] = ul_value
        df["EXPIRY_DATE"] = curr_expiry_date
        df["TIMESTAMP"] = timestamp

        # Print the DataFrame
        print(f"\n{index_name} DataFrame:")
        print(df)

        return df
    else:
        print(f"Failed to retrieve options data for {index_name}.")
        return None


def save_to_csv(dataframe, index_name):
    """Save DataFrame to CSV file."""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    month = datetime.datetime.now().strftime('%Y-%m')
    folder_path = f"data/{index_name}/{month}"

    # Create folders if they don't exist
    os.makedirs(folder_path, exist_ok=True)

    # Save DataFrame to CSV
    csv_path = f"{folder_path}/{index_name}_{today}.csv"

    # If the CSV file already exists, append the data
    if os.path.exists(csv_path):
        existing_data = pd.read_csv(csv_path)
        combined_data = pd.concat([existing_data, dataframe], ignore_index=True)
        combined_data.to_csv(csv_path, index=False)
    else:
        dataframe.to_csv(csv_path, index=False)

    print(f"Data saved to {csv_path}")

def is_market_open():
    """Check if the market is open between 9:15 am and 3:30 pm."""
    now = datetime.datetime.now().time()
    market_open = datetime.time(9, 15)
    market_close = datetime.time(15, 30)

    return market_open <= now <= market_close

while True:
    # Check if the market is open
    if is_market_open():
        # Run the job every 3 minutes
        set_header()

        # Fetch data for Nifty and Bank Nifty
        nifty_df = print_oi(10, 50, nf_nearest, API_ENDPOINTS['nf'], "Nifty", nf_ul)
        banknifty_df = print_oi(10, 100, bnf_nearest, API_ENDPOINTS['bnf'], "Bank Nifty", bnf_ul)

        # Save data to CSV
        save_to_csv(nifty_df, "nifty")
        save_to_csv(banknifty_df, "banknifty")

    # Sleep for 3 minutes + 20 seconds gap
    time.sleep(200)

# Main execution logic
set_header()
print("\033c")  # Clear console (Note: This may not work in some environments)
print_hr()
print_header("Nifty", nf_ul, nf_nearest)
print_hr()
# Call the function to get DataFrames for Nifty and Bank Nifty
nifty_df = print_oi(10, 50, nf_nearest, API_ENDPOINTS['nf'], "Nifty", nf_ul)

print_hr()
print_header("Bank Nifty", bnf_ul, bnf_nearest)
print_hr()
banknifty_df = print_oi(10, 100, bnf_nearest, API_ENDPOINTS['bnf'], "Bank Nifty", bnf_ul)

nf_highestoi_CE = highest_oi("CE", 10, 50, nf_nearest, API_ENDPOINTS['nf'])
nf_highestoi_PE = highest_oi("PE", 10, 50, nf_nearest, API_ENDPOINTS['nf'])
bnf_highestoi_CE = highest_oi("CE", 10, 100, bnf_nearest, API_ENDPOINTS['bnf'])
bnf_highestoi_PE = highest_oi("PE", 10, 100, bnf_nearest, API_ENDPOINTS['bnf'])



print(color_text("Major Support in Nifty: ", COLORS["cyan"]) + str(nf_highestoi_CE))
print(color_text("Major Resistance in Nifty: ", COLORS["cyan"]) + str(nf_highestoi_PE))
print(color_text("Major Support in Bank Nifty: ", COLORS["purple"]) + str(bnf_highestoi_CE))
print(color_text("Major Resistance in Bank Nifty: ", COLORS["purple"]) + str(bnf_highestoi_PE))



