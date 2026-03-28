import requests
import logging

logger = logging.getLogger(__name__)

class ExchangeRateClient:
    def __init__(self):
        self.fiat_url = "https://api.exchangerate-api.com/v4/latest/"
        self.crypto_url = "https://api.coingecko.com/api/v3/simple/price"
        
        # Mapping common symbols to coingecko ids
        self.crypto_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDT': 'tether',
            'XRP': 'ripple',
            'TRX': 'tron',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'DOGE': 'dogecoin',
            'ADA': 'cardano'
        }
        
        # Fiat currencies typically supported by exchangerate-api
        self.fiat_currencies = ['USD', 'KRW', 'EUR', 'JPY', 'CNY', 'GBP', 'AUD', 'CAD']

    def is_crypto(self, symbol):
        return symbol.upper() in self.crypto_map

    def is_fiat(self, symbol):
        return symbol.upper() in self.fiat_currencies

    def get_crypto_price_in_usd(self, crypto_symbol):
        cg_id = self.crypto_map.get(crypto_symbol.upper())
        if not cg_id:
            return None
            
        try:
            resp = requests.get(self.crypto_url, params={'ids': cg_id, 'vs_currencies': 'usd'}, timeout=5)
            data = resp.json()
            return data.get(cg_id, {}).get('usd')
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
            return None

    def get_fiat_rate(self, base_fiat, target_fiat):
        try:
            resp = requests.get(f"{self.fiat_url}{base_fiat.upper()}", timeout=5)
            data = resp.json()
            return data.get('rates', {}).get(target_fiat.upper())
        except Exception as e:
            logger.error(f"ExchangeRate API error: {e}")
            return None

    def convert(self, amount, from_symbol, to_symbol):
        from_symbol = from_symbol.upper()
        to_symbol = to_symbol.upper()
        
        # Case 1: Fiat to Fiat
        if self.is_fiat(from_symbol) and self.is_fiat(to_symbol):
            rate = self.get_fiat_rate(from_symbol, to_symbol)
            if rate:
                return amount * rate
            return None

        # Case 2: Crypto to Crypto
        if self.is_crypto(from_symbol) and self.is_crypto(to_symbol):
            from_usd = self.get_crypto_price_in_usd(from_symbol)
            to_usd = self.get_crypto_price_in_usd(to_symbol)
            if from_usd and to_usd:
                return amount * (from_usd / to_usd)
            return None

        # Case 3: Crypto to Fiat
        if self.is_crypto(from_symbol) and self.is_fiat(to_symbol):
            crypto_usd = self.get_crypto_price_in_usd(from_symbol)
            if not crypto_usd:
                return None
            
            if to_symbol == 'USD':
                return amount * crypto_usd
                
            usd_to_fiat_rate = self.get_fiat_rate('USD', to_symbol)
            if usd_to_fiat_rate:
                return amount * crypto_usd * usd_to_fiat_rate
            return None

        # Case 4: Fiat to Crypto
        if self.is_fiat(from_symbol) and self.is_crypto(to_symbol):
            crypto_usd = self.get_crypto_price_in_usd(to_symbol)
            if not crypto_usd:
                return None
                
            usd_amount = amount
            if from_symbol != 'USD':
                fiat_to_usd_rate = self.get_fiat_rate(from_symbol, 'USD')
                if not fiat_to_usd_rate:
                    return None
                usd_amount = amount * fiat_to_usd_rate
                
            return usd_amount / crypto_usd

        return None

exchange_client = ExchangeRateClient()
