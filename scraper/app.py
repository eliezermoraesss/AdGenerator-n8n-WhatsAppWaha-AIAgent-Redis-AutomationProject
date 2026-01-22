from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import re
import requests
from urllib.parse import urlparse
import os

app = FastAPI()

def is_amazon(url):
    return "amazon." in url or "amzn." in url

def is_mercado_livre(url):
    return "mercadolivre" in url

def normalize_price_from_aria(label: str):
    """
    Ex: '486 reais com 76 centavos' -> 'R$ 486,76'
    """
    numbers = re.findall(r'\d+', label)
    if not numbers:
        return None
    if len(numbers) == 1:
        return f"R$ {numbers[0]},00"
    return f"R$ {numbers[0]},{numbers[1]}"

def download_and_convert_image(url: str):
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".jpg"

    filename = f"/tmp/image{ext}"
    r = requests.get(url, timeout=30)
    with open(filename, "wb") as f:
        f.write(r.content)

    return filename

@app.post("/scrape")
def scrape(data: dict):
    url = data.get("url")

    if not url:
        return {"error": "URL não informada"}

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

            botao = page.locator(
                "a.poly-component__link--action-link:has-text('Ir para produto')"
            )

            if botao.count() > 0:
                botao.first.click()
                page.wait_for_load_state("domcontentloaded")

            # ESPERA PELO ELEMENTO REAL
            page.wait_for_selector("h1.ui-pdp-title", timeout=60000)

            titulo = page.locator("h1.ui-pdp-title").first.inner_text().strip()

            preco_atual = None
            price_locator = page.locator("span[itemprop='offers']")
            if price_locator.count() > 0:
                aria = price_locator.first.get_attribute("aria-label")
                if aria:
                    preco_atual = normalize_price_from_aria(aria)

            preco_anterior = None
            old_price_locator = page.locator(
                "s.andes-money-amount.andes-money-amount--previous"
            )

            if old_price_locator.count() > 0:
                aria = old_price_locator.first.get_attribute("aria-label")
                if aria:
                    preco_anterior = normalize_price_from_aria(aria)

            imagem_url = None
            img_locator = page.locator(
                "img.ui-pdp-image.ui-pdp-gallery__figure__image"
            )

            if img_locator.count() > 0:
                imagem_url = (
                    img_locator.first.get_attribute("data-zoom")
                    or img_locator.first.get_attribute("src")
    )

        # ===== AMAZON =====
        elif is_amazon(url):
            page.wait_for_selector("#titleSection", timeout=60000)
            page.wait_for_selector("#apex_desktop", timeout=60000)

            # Título
            titulo = page.locator("#titleSection #productTitle").inner_text().strip()

            # Preço atual
            apex = page.locator("#apex_desktop")
            preco_atual = None
            price = apex.locator("span.priceToPay")
            if price.count() > 0:
                preco_atual = (
                    price.locator(".a-price-whole").first.inner_text().replace("\n","")
                    + price.locator(".a-price-fraction").first.inner_text()
                )
                
            # Preço anterior
            preco_anterior = None
            old_price_locator = page.locator(
                "span.a-size-small.aok-offscreen:has-text('De:')"
            )

            if old_price_locator.count() > 0:
                texto = old_price_locator.first.inner_text()
                preco_anterior = texto.replace("De:", "").strip()

            if page.locator("#landingImage").count() > 0:
                imagem_url = page.locator("#landingImage").get_attribute("data-old-hires") \
                              or page.locator("#landingImage").get_attribute("src")

        else:
            browser.close()
            return {"error": "Plataforma não suportada"}

        browser.close()

        imagem_local = None
        if imagem_url:
            imagem_local = download_and_convert_image(imagem_url)

        return {
            "titulo": titulo,
            "preco_atual": preco_atual,
            "preco_anterior": preco_anterior,
            "imagem_url": imagem_url,
            "imagem_local": imagem_local,
            "url": url
        }
