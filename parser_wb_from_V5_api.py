import requests


def get_products(query, page=1):
    url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {
        "query": query,
        "page": page,
        "resultset": "catalog",
        "appType": 1,
        "curr": "byn",
        "dest": -59208,
        "sort": "popular",
        "spp": 0,
        "locale": "by"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    count = 0

    products = data['data']['products']

    for product in products:
        id_product = product.get('id')
        price = products[0]["sizes"][0]["price"].get("basic") / 100
        discount = products[0]["sizes"][0]["price"].get("product") / 100  # может отсутствовать
        rating = product.get("reviewRating", 0)
        feedbacks = product.get("feedbacks", 0)

        count += 1

        print({
            "id": id_product,
            "title": product["name"],
            "price": price,
            "discount_price": discount if discount else price,  # если нет скидки
            "rating": rating,
            "feedbacks": feedbacks
        })
    print(count)

get_products("трусики", 2)
