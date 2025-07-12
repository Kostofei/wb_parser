import time

from DrissionPage import ChromiumPage
from DrissionPage._functions.keys import Keys



page = ChromiumPage()

SEARCH_QUERY = "носки"
category_url = 'https://www.wildberries.ru'
page.get(category_url)


search = page.ele('#searchInput')
search.focus()
time.sleep(0.2)
search.input(SEARCH_QUERY)
page.actions.type(Keys.ENTER)


num_page = 0
def group_item():
    global num_page
    count = 0
    time.sleep(0.5)
    while len(page.ele('.product-card-list').children()) != 100:
        time.sleep(0.5)
        page.scroll.to_see(page.ele('.product-card-list').children()[-1])
        if count > 3:
            page.scroll.to_top()
        time.sleep(0.5)
        count += 1
    script = """
    const items = document.querySelector('.product-card-list').children
    const itemList = []
            items.forEach(item => {
                itemList.push({
            title: item.querySelector('.product-card__name').innerText.replace(/^ ?\/ ?/, '') || '',
            price: item.querySelector('del')?.innerText.replace(/\u00A0/g, ' ') || '',
            discounted_price: item.querySelector('.price__lower-price')?.innerText.replace(/\u00A0/g, ' ') || '',
            rating: item.querySelector('.address-rate-mini')?.innerText.replace(/\u00A0/g, ' ') || '',
            rating_count: item.querySelector('.product-card__count')?.innerText.replace(/\u00A0/g, ' ') || ''
    });
    })

    return itemList
    """
    items = page.run_js(script)
    num_page += 1
    print(f"Страница {num_page}")
    return items

def next_page():
    page.ele('text:Следующая страница').click()


while True:
    x = group_item()
    print(x)
    next_page()
