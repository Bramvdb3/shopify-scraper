import requests
import time
import json
from datetime import datetime

SHOP_URL = "https://shop-toxictees.com/products.json"  # <-- Vul hier de echte winkel in
MARGE_PERCENTAGE = 0.3  # 30% winst

def get_products(shop_url):
    response = requests.get(f"{shop_url}/products.json?limit=250")
    if response.status_code == 200:
        return response.json().get("products", [])
    else:
        print("Kan producten niet ophalen.")
        return []

def get_variant_inventory(shop_url, variant_id):
    # Shopify trick: voeg een productvariant toe aan cart en kijk naar inventory
    url = f"{shop_url}/cart/add.js"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = f"id={variant_id}&quantity=1"
    try:
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            return 9999  # Soms komt er geen fout = voorraad onbekend (onbeperkt)
        elif response.status_code == 422:
            error_msg = response.json().get("description", "")
            parts = error_msg.split("You can only add ")
            if len(parts) > 1:
                try:
                    qty = int(parts[1].split()[0])
                    return qty
                except:
                    return -1
        return -1
    except Exception as e:
        print("Fout bij voorraad check:", e)
        return -1

def analyse_shop(shop_url):
    producten = get_products(shop_url)
    analyse_resultaat = []

    for product in producten:
        title = product['title']
        variant = product['variants'][0]
        variant_id = variant['id']
        price = float(variant['price'])

        inventory = get_variant_inventory(shop_url, variant_id)
        analyse_resultaat.append({
            'title': title,
            'variant_id': variant_id,
            'price': price,
            'inventory': inventory
        })
        time.sleep(1)  # Shopify blokkeren voorkomen

    return analyse_resultaat

def vergelijk_met_oude_data(nieuwe_data, oude_data):
    totaal_omzet = 0
    totaal_winst = 0
    resultaat = []

    oude_dict = {item['variant_id']: item for item in oude_data}

    for item in nieuwe_data:
        variant_id = item['variant_id']
        huidige_voorraad = item['inventory']
        oude_voorraad = oude_dict.get(variant_id, {}).get('inventory', huidige_voorraad)
        verkocht = max(0, oude_voorraad - huidige_voorraad)
        omzet = verkocht * item['price']
        winst = omzet * MARGE_PERCENTAGE

        resultaat.append({
            'title': item['title'],
            'verkocht': verkocht,
            'omzet': omzet,
            'winst': winst
        })

        totaal_omzet += omzet
        totaal_winst += winst

    return resultaat, totaal_omzet, totaal_winst

def main():
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    nieuwe_data = analyse_shop(SHOP_URL)

    try:
        with open("shopify_voorraad_snapshot.json", "r") as f:
            oude_data = json.load(f)
    except FileNotFoundError:
        print("Geen oude voorraaddata gevonden. Maak eerste snapshot aan.")
        oude_data = nieuwe_data
        with open("shopify_voorraad_snapshot.json", "w") as f:
            json.dump(nieuwe_data, f, indent=2)
        return

    resultaten, omzet, winst = vergelijk_met_oude_data(nieuwe_data, oude_data)

    print(f"\n📊 Resultaten sinds vorige meting:")
    for r in resultaten:
        if r['verkocht'] > 0:
            print(f"{r['title']} | Verkocht: {r['verkocht']} | Omzet: €{r['omzet']:.2f} | Winst: €{r['winst']:.2f}")

    print(f"\n💰 Totale omzet: €{omzet:.2f}")
    print(f"📈 Totale winst: €{winst:.2f}")

    # Update snapshot
    with open("shopify_voorraad_snapshot.json", "w") as f:
        json.dump(nieuwe_data, f, indent=2)

if __name__ == "__main__":
    main()
