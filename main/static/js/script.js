const apiURLFilter = 'http://127.0.0.1:8000/api/v1/products/search/';
const apiURLDelete = 'http://127.0.0.1:8000/api/v1/products/delete_all/'

let currentSort = {key: null, asc: true};
let currentProducts = [];

const filterFields = [
    "min_price", "max_price",
    "min_rating",
    "min_reviews_count",
];

let tbody;
let priceHistogramChart;
let discountRatingChart;

// Функция для получения CSRF-токена из куки
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', () => {
    tbody = document.querySelector("#productTable tbody");

    // Обработка клика по кнопке "Применить фильтры"
    document.getElementById('applyFilters').addEventListener('click', () => {
        console.log("Клик работает");
        fetchProducts();
    });

    // Обработка клика по кнопке "Очистить фильтры"
    document.getElementById('clearFilters').addEventListener('click', () => {
        filterFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        console.log("Фильтры очищены");
        fetchProducts();
    });

    // Обработка клика по кнопке "Полная очистка БД"
    document.getElementById('purge-database').addEventListener('click', async () => {
        try {
            const csrfToken = getCookie('csrftoken');
            const deleteResponse = await fetch(apiURLDelete, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'include'
            });

            if (!deleteResponse.ok) {
                const errorText = await deleteResponse.text();
                throw new Error(`Ошибка ${deleteResponse.status}: ${errorText}`);
            }

            await fetchProducts();

        } catch (error) {
            console.error('Произошла ошибка:', error);
            alert('Не удалось выполнить операцию: ' + error.message);
        }
    });

    // Обработка клика по заголовкам таблицы (сортировка)
    document.querySelectorAll("#productTable th").forEach(th => {
        th.addEventListener("click", () => {
            const key = th.getAttribute("data-sort");
            if (currentSort.key === key) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.key = key;
                currentSort.asc = true;
            }
            renderTable();
        });
    });

    fetchProducts();
});

async function fetchProducts() {
    const params = new URLSearchParams();

    filterFields.forEach(id => {
        const value = document.getElementById(id).value;
        if (value) params.append(id, value);
    });

    const url = apiURLFilter + '?' + params.toString();

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Ошибка загрузки данных');
        const data = await res.json();

        currentProducts = data;
        renderTable();
    } catch (e) {
        console.error(e);
        tbody.innerHTML = `<tr><td colspan="5">Ошибка загрузки данных</td></tr>`;
    }
}

function sortProducts(productsList) {
    if (!currentSort.key) return productsList;
    return productsList.slice().sort((a, b) => {
        let valA = a[currentSort.key];
        let valB = b[currentSort.key];

        if (currentSort.key === 'title') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
            return currentSort.asc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else {
            return currentSort.asc ? valA - valB : valB - valA;
        }
    });
}

function renderTable() {
    const sorted = sortProducts(currentProducts);
    tbody.innerHTML = "";

    if (sorted.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5">Нет товаров</td></tr>`;
        updateCharts([]);
        return;
    }

    for (const p of sorted) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${p.title ?? ''}</td>
            <td>${Number(p.price ?? 0).toFixed(2)}</td>
            <td>${Number(p.discounted_price ?? 0).toFixed(2)}</td>
            <td>${Number(p.rating ?? 0).toFixed(1)}</td>
            <td>${Number(p.reviews_count ?? 0)}</td>
        `;
        tbody.appendChild(tr);
    }

    updateCharts(sorted);
}

function updateCharts(productsList) {
    // Histogram: распределение по цене
    const priceBuckets = {};
    for (let i = 0; i <= 10000; i += 1000) {
        priceBuckets[`${i}-${i + 999}`] = 0;
    }
    productsList.forEach(p => {
        const price = Number(p.price);
        const bucketKey = `${Math.floor(price / 1000) * 1000}-${Math.floor(price / 1000) * 1000 + 999}`;
        if (priceBuckets[bucketKey] !== undefined) {
            priceBuckets[bucketKey]++;
        }
    });

    const labels = Object.keys(priceBuckets);
    const counts = Object.values(priceBuckets);

    if (!priceHistogramChart) {
        priceHistogramChart = new Chart(document.getElementById('priceHistogram').getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Товары',
                    data: counts,
                    backgroundColor: 'rgba(54,162,235,0.6)'
                }]
            },
            options: {
                scales: {y: {beginAtZero: true}}
            }
        });
    } else {
        priceHistogramChart.data.labels = labels;
        priceHistogramChart.data.datasets[0].data = counts;
        priceHistogramChart.update();
    }

    // Line chart: скидка vs рейтинг
    const sortedByRating = productsList.slice().sort((a, b) => a.rating - b.rating);
    const ratingData = sortedByRating.map(p => Number(p.rating));
    const discountData = sortedByRating.map(p => Number(p.price) - Number(p.discounted_price));

    if (!discountRatingChart) {
        discountRatingChart = new Chart(document.getElementById('discountRatingChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: ratingData,
                datasets: [{
                    label: 'Скидка',
                    data: discountData,
                    borderColor: 'rgba(255,99,132,0.8)',
                    fill: false,
                    tension: 0.3
                }]
            },
            options: {
                scales: {
                    x: {title: {display: true, text: 'Рейтинг'}},
                    y: {title: {display: true, text: 'Скидка'}, beginAtZero: true}
                }
            }
        });
    } else {
        discountRatingChart.data.labels = ratingData;
        discountRatingChart.data.datasets[0].data = discountData;
        discountRatingChart.update();
    }
}
