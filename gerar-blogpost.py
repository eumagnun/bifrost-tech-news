import os
import re
import math
import requests
import base64
import io
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from PIL import Image as PILImage
import markdown
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o cliente unificado utilizando a chave de API do ambiente
client = genai.Client(
    api_key=os.environ.get("GOOGLE_API_KEY"),
)

def get_top_hacker_news_story():
    """
    Faz o scraping da página inicial do Hacker News e retorna o post mais votado
    do momento (evitando links de jobs ou posts sem pontuação).
    """
    url = "https://news.ycombinator.com/news"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erro ao acessar o Hacker News: {response.status_code}")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Seleciona todas as linhas principais de posts (class 'athing')
    stories = soup.find_all('tr', class_='athing')
    
    for story in stories:
        story_id = story.get('id')
        
        # A linha de subtexto é SEMPRE a próxima tag 'tr' irmã da linha do título
        subtext_row = story.find_next_sibling('tr')
        if not subtext_row:
            continue
            
        # Busca o span de pontuação dentro da linha de subtexto
        score_span = subtext_row.find('span', class_='score')
        
        # Se tem score_span, significa que é um post com votação ativa (ignora vagas de emprego/anúncios)
        if score_span:
            title_line = story.find('span', class_='titleline')
            if title_line:
                link_tag = title_line.find('a')
                title = link_tag.text
                link = link_tag.get('href')
                
                # Se o link for interno do HN (ex: "item?id=..."), formata a URL cheia
                if link.startswith('item?id='):
                    link = f"https://news.ycombinator.com/{link}"
                    
                return {
                    "title": title,
                    "link": link,
                    "hn_link": f"https://news.ycombinator.com/item?id={story_id}"
                }
                
    raise Exception("Nenhum post válido encontrado.")
def generate_ptbr_content(title: str) -> str:
    """
    Utiliza o Gemini 3.1 Flash-Lite para traduzir, contextualizar e criar o corpo
    do post em português com base no título do Hacker News.
    """
    model_id = "gemini-3.1-flash-lite"
    
    prompt = f"""
    Você é um Arquiteto de Soluções sênior e criador de conteúdo técnico focado em tecnologia e inovação.
    Com base no seguinte tópico quente do Hacker News: "{title}", crie um post COMPLETO, engajador e didático em Português do Brasil (PT-BR) para um blog técnico.

    REQUISITOS OBRIGATÓRIOS:
    - O texto DEVE ter no mínimo 2000 palavras. Desenvolva cada seção com profundidade.
    - Todo o conteúdo deve estar em Português do Brasil (PT-BR).

    ESTRUTURA DO POST:
    1. **Título chamativo** — Em português, criativo e que desperte curiosidade.
    2. **Introdução (2-3 parágrafos)** — Contextualize o tema, explique por que ele é relevante agora e qual problema ele resolve.
    3. **O que é e como funciona (3-4 parágrafos)** — Explicação técnica aprofundada do conceito, com detalhes de arquitetura, protocolos ou mecanismos envolvidos.
    4. **Por que isso importa (2-3 parágrafos)** — Impacto no mercado, na comunidade de desenvolvedores e nas empresas. Inclua dados ou tendências quando possível.
    5. **Caso de Uso: Explicando com Dragon Ball 🐉** — Esta é a seção mais criativa e importante. Crie uma analogia DETALHADA usando o universo de Dragon Ball para explicar o conceito técnico de forma simplificada e divertida. Use personagens como Goku, Vegeta, Bulma, Piccolo, Gohan, etc. Estruture como uma pequena narrativa onde os personagens enfrentam um problema que é resolvido pelo conceito tecnológico do artigo. Exemplo: se o tema for "load balancing", Goku poderia distribuir o ki entre os guerreiros Z como um balanceador de carga. Desenvolva a analogia com pelo menos 4-5 parágrafos, tornando-a rica e educativa.
    6. **Aplicações práticas e exemplos reais (2-3 parágrafos)** — Como empresas e projetos reais utilizam essa tecnologia.
    7. **Conclusão e reflexão (1-2 parágrafos)** — Feche com um gancho para o leitor, provocando reflexão sobre o futuro do tema.

    DIRETRIZES DE ESTILO:
    - Tom profissional, porém leve, acessível e com toques de humor geek.
    - Use emojis estrategicamente para melhorar a legibilidade (🚀, 💡, ⚡, 🐉, etc.).
    - Inclua subtítulos claros para cada seção.
    - Não invente links ou referências fictícias.
    - O caso de uso com Dragon Ball deve ser tecnicamente preciso na analogia, mesmo sendo divertido.
    """
    
    # Configuração explícita utilizando o padrão fornecido
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level="LOW",
        ),
    )
    
    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=generate_content_config
    )
    return response.text

def generate_mascot_image_via_interaction(theme: str, output_path="post_image.png"):
    """
    Utiliza o modelo multimodal gemini-3.1-flash-lite-image via client.interactions
    para gerar a ilustração do Nano Bana integrado ao tema técnico.
    """
    model_id = 'models/gemini-3.1-flash-lite-image'
    
    # Prompt estruturado para gerar ilustração estilo anime Dragon Ball com o Nano Bana
    prompt = (
        f"A vibrant anime illustration in the style of Dragon Ball Z / Dragon Ball Super by Akira Toriyama. "
        f"The scene features a cute, powerful mascot character named 'Nano Bana' — a small warrior with a banana-shaped head, "
        f"glowing yellow aura like a Super Saiyan, wearing a Saiyan battle armor with nanotech circuit patterns. "
        f"Nano Bana is striking a dynamic battle pose, surrounded by energy effects and ki blasts, "
        f"in a scene that visually represents the theme: {theme}. "
        f"The background should include iconic Dragon Ball elements (energy beams, floating rocks, dramatic sky). "
        f"Anime cel-shading style, bold outlines, vibrant saturated colors, dynamic action composition, epic lighting, high resolution."
    )
    
    print(f"Gerando imagem via Interaction com o modelo: {model_id}")
    
    generation_config = {
        'temperature': 1,
        'max_output_tokens': 65536,
        'top_p': 0.95,
        'thinking_level': 'low',
    }
    
    interaction = client.interactions.create(
        model=model_id,
        input=prompt,
        generation_config=generation_config,
        response_modalities=['image', 'text'],
    )
    
    # Varre a resposta da interação para coletar e salvar os bytes da imagem
    for step in interaction.steps:
        if step.type == 'model_output' and step.content:
            for part in step.content:
                if part.type == 'image':
                    image_data = base64.b64decode(part.data)
                    image = PILImage.open(io.BytesIO(image_data))
                    image.save(output_path)
                    return output_path
                    
    raise Exception("A API de interação não retornou nenhuma imagem válida.")

def render_html_post(title: str, content_md: str, image_path: str,
                     original_link: str, hn_link: str,
                     output_path: str = "post.html"):
    """
    Converte o conteúdo Markdown gerado em HTML e injeta no template,
    produzindo o arquivo final do post estilizado.
    """
    # Caminho do template relativo ao script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Converte o Markdown do post para HTML
    content_html = markdown.markdown(
        content_md,
        extensions=["extra", "codehilite", "nl2br", "sane_lists"]
    )

    # Estima tempo de leitura (~200 palavras por minuto)
    word_count = len(re.findall(r'\w+', content_md))
    reading_time = max(1, math.ceil(word_count / 200))

    # Gera a meta description a partir das primeiras palavras do conteúdo
    plain_text = re.sub(r'[#*_`\[\]()>\-!]', '', content_md)
    meta_description = ' '.join(plain_text.split()[:30]) + '...'

    # Data formatada em PT-BR
    date_str = datetime.now().strftime("%d/%m/%Y")

    # Substitui os placeholders no template
    html_output = template.replace("{{TITLE}}", title)
    html_output = html_output.replace("{{CONTENT}}", content_html)
    html_output = html_output.replace("{{IMAGE_PATH}}", image_path)
    html_output = html_output.replace("{{ORIGINAL_LINK}}", original_link)
    html_output = html_output.replace("{{HN_LINK}}", hn_link)
    html_output = html_output.replace("{{DATE}}", date_str)
    html_output = html_output.replace("{{READING_TIME}}", str(reading_time))
    html_output = html_output.replace("{{META_DESCRIPTION}}", meta_description)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    return output_path


def main():
    try:
        print("1. Buscando o post mais relevante do Hacker News...")
        story = get_top_hacker_news_story()
        print(f"Encontrado: {story['title']}")
        print(f"Link Original: {story['link']}")

        print("\n2. Gerando a versão adaptada em PT-BR com o Gemini 3.1 Flash-Lite...")
        post_text = generate_ptbr_content(story['title'])

        print("\n3. Gerando a imagem com o Nano Bana via Gemini 3.1 Flash-Lite Image...")
        image_file = generate_mascot_image_via_interaction(story['title'])

        print("\n4. Renderizando o post em HTML com o template...")
        html_file = render_html_post(
            title=story['title'],
            content_md=post_text,
            image_path=image_file,
            original_link=story['link'],
            hn_link=story['hn_link']
        )

        print("\n--- POST GERADO COM SUCESSO ---")
        print(post_text)
        print("\n🔗 Fontes e Créditos:")
        print(f"👉 Artigo Original: {story['link']}")
        print(f"💬 Discussão no HN: {story['hn_link']}")
        print(f"🖼️ Imagem gerada: {image_file}")
        print(f"📄 Post HTML: {html_file}")
        print("--------------------------------")

    except Exception as e:
        print(f"Ocorreu um erro na execução: {e}")

if __name__ == "__main__":
    main()