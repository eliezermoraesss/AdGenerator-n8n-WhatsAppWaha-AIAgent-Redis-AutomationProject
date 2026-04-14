from fastapi import FastAPI
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re

app = FastAPI()

def is_amazon(url):
    return "amazon." in url or "amzn." in url

def is_mercado_livre(url):
    return "mercadolivre" in url or "meli.la" in url

def normalize_price_from_aria(label: str):
    numbers = re.findall(r'\d+', label)
    if not numbers:
        return None
    if len(numbers) == 1:
        return f"R$ {numbers[0]},00"
    return f"R$ {numbers[0]},{numbers[1]}"

@app.post("/scrape")
def scrape(data: dict):
    url = data.get("url")

    if not url:
        return {
            "status": "error",
            "error_type": "INVALID_INPUT",
            "message": "URL não informada"
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )

            page.goto(url, timeout=60000)

            titulo = None
            preco_atual = None
            preco_anterior = None
            imagem_url = None

            # ===== MERCADO LIVRE =====
            if is_mercado_livre(url):
                page.wait_for_load_state("domcontentloaded")

                # Tenta encontrar a lista de recomendações
                recommendations = page.locator("div.ui-recommendations-list__container--single")
                if recommendations.count() > 0:
                    # Pega o primeiro card de produto
                    card = recommendations.locator("div.poly-card").first

                    # Título
                    titulo = card.locator("a.poly-component__title").first.inner_text().strip()

                    # Preço atual
                    price_locator = card.locator("div.poly-price__current span.andes-money-amount")
                    if price_locator.count() > 0:
                        aria = price_locator.first.get_attribute("aria-label")
                        if aria:
                            preco_atual = normalize_price_from_aria(aria)

                    # Preço anterior
                    old_price_locator = card.locator("s.andes-money-amount.andes-money-amount--previous")
                    if old_price_locator.count() > 0:
                        aria = old_price_locator.first.get_attribute("aria-label")
                        if aria:
                            preco_anterior = normalize_price_from_aria(aria)

                    # Imagem
                    img_locator = card.locator("img.poly-component__picture")
                    if img_locator.count() > 0:
                        imagem_url = img_locator.first.get_attribute("src")

            # ===== AMAZON =====
            elif is_amazon(url):
                page.wait_for_load_state("domcontentloaded")

                titulo = page.locator("#titleSection #productTitle").inner_text().strip()

                price = page.locator("div.a-section.apex-core-price-identifier").first
                if price.count() > 0:
                    offscreen_price = price.locator("span.a-offscreen").first
                    if offscreen_price.count() > 0:
                        preco_atual = offscreen_price.inner_text().strip()

                    if not preco_atual:
                        whole = price.locator("span.a-price-whole").first
                        fraction = price.locator("span.a-price-fraction").first
                        if whole.count() > 0 and fraction.count() > 0:
                            preco_atual = (
                                f"R$ {whole.inner_text().replace(',', '').replace('.', '').strip()},"
                                f"{fraction.inner_text().strip()}"
                            )

                old_price_locator = page.locator(
                    "span.a-size-small.aok-offscreen:has-text('De:')"
                )
                if old_price_locator.count() > 0:
                    preco_anterior = old_price_locator.first.inner_text().replace("De:", "").strip()

                if page.locator("#landingImage").count() > 0:
                    raw_img = (
                        page.locator("#landingImage").get_attribute("data-old-hires")
                        or page.locator("#landingImage").get_attribute("src")
                    )
                    imagem_url = re.sub(r"_SL\d+_", "_SL800_", raw_img)

            else:
                browser.close()
                return {
                    "status": "error",
                    "error_type": "UNSUPPORTED_PLATFORM",
                    "message": "Plataforma não suportada",
                    "url": url
                }

            browser.close()

            return {
                "status": "success",
                "titulo": titulo,
                "preco_atual": preco_atual,
                "preco_anterior": preco_anterior,
                "imagem_url": imagem_url,
                "url": url
            }

    except PlaywrightTimeoutError:
        return {
            "status": "error",
            "error_type": "TIMEOUT",
            "message": "Timeout ao aguardar elementos da página",
            "url": url
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": "SCRAPE_ERROR",
            "message": str(e),
            "url": url
        }
