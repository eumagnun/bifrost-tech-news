import os
import re
import math
import requests
import base64
import io
import json
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
    - Comece o texto DIRETAMENTE com o título. Não adicione conversas amigáveis no início ou no fim (ex: "Aqui está o post solicitado", "Espero que goste").
    - Não envolva a resposta completa em um bloco de código markdown (como ```markdown ... ```).
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
    
    text = response.text.strip()
    
    # Remove wrappers de bloco de código markdown se houver
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
        
    # Remove saudações e introduções conversacionais comuns
    preambles = [
        "aqui está o seu post", "aqui está o post", "aqui está um post",
        "segue o post", "claro! aqui está", "com certeza, aqui está",
        "olá! aqui está", "segue abaixo o post", "aqui está o artigo"
    ]
    for preamble in preambles:
        if text.lower().startswith(preamble):
            # Procura o primeiro título (# ou ##) ou linha com texto e remove o preâmbulo
            lines = text.split("\n")
            cleaned_lines = []
            heading_found = False
            for line in lines:
                if line.strip().startswith("#"):
                    heading_found = True
                if heading_found:
                    cleaned_lines.append(line)
            if cleaned_lines:
                text = "\n".join(cleaned_lines).strip()
            break
            
    return text

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

def slugify(text: str) -> str:
    """
    Converte um texto para um slug URL amigável.
    """
    # Converte para minúsculas e remove acentos/caracteres especiais simples
    text = text.lower()
    # Substitui caracteres não alfanuméricos por hífen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove hífens múltiplos ou nas pontas
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text if text else "post"

def render_html_post(title: str, content_md: str, image_filename: str,
                     original_link: str, hn_link: str,
                     output_path: str) -> tuple[int, str]:
    """
    Converte o conteúdo Markdown gerado em HTML e injeta no template,
    produzindo o arquivo final do post estilizado. Retorna uma tupla (reading_time, excerpt).
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
    excerpt = ' '.join(plain_text.split()[:30]) + '...'

    # Data formatada em PT-BR
    date_str = datetime.now().strftime("%d/%m/%Y")

    # Caminho da imagem relativo ao arquivo HTML do post (está na pasta posts/images/...)
    rel_image_path = f"images/{image_filename}"

    # Substitui os placeholders no template
    html_output = template.replace("{{TITLE}}", title)
    html_output = html_output.replace("{{CONTENT}}", content_html)
    html_output = html_output.replace("{{IMAGE_PATH}}", rel_image_path)
    html_output = html_output.replace("{{ORIGINAL_LINK}}", original_link)
    html_output = html_output.replace("{{HN_LINK}}", hn_link)
    html_output = html_output.replace("{{DATE}}", date_str)
    html_output = html_output.replace("{{READING_TIME}}", str(reading_time))
    html_output = html_output.replace("{{META_DESCRIPTION}}", excerpt)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    return reading_time, excerpt

def update_posts_metadata(title: str, date_str: str, slug: str, image_filename: str,
                          original_link: str, hn_link: str, reading_time: int, excerpt: str):
    """
    Carrega, atualiza e salva o arquivo posts.json com o novo post no início da lista.
    """
    metadata_path = "posts.json"
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                posts = json.load(f)
        except Exception:
            posts = []
    else:
        posts = []

    # Cria o novo registro
    new_post = {
        "slug": slug,
        "title": title,
        "date": date_str,
        "image_path": f"posts/images/{image_filename}",
        "original_link": original_link,
        "hn_link": hn_link,
        "reading_time": reading_time,
        "excerpt": excerpt
    }

    # Verifica se já existe um post com a mesma slug ou link original
    existing_index = -1
    for i, p in enumerate(posts):
        if p["slug"] == slug or p["original_link"] == original_link:
            existing_index = i
            break

    if existing_index != -1:
        # Atualiza o registro existente
        posts[existing_index] = new_post
    else:
        # Insere no início da lista
        posts.insert(0, new_post)

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    return posts

def generate_list_pages(posts: list):
    """
    Gera index.html (últimos 10 posts) e archive.html (todos os posts).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    list_template_path = os.path.join(script_dir, "list_template.html")

    if not os.path.exists(list_template_path):
        raise FileNotFoundError(f"Template de lista não encontrado em: {list_template_path}")

    with open(list_template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Função auxiliar para gerar blocos de HTML dos posts
    def build_hero_html(post):
        return f"""
        <article class="hero-post">
            <div class="hero-image-wrapper">
                <img src="{post['image_path']}" alt="{post['title']}">
            </div>
            <div class="hero-info">
                <div class="post-tag">Último Post</div>
                <a href="posts/{post['slug']}.html" class="hero-post-title">{post['title']}</a>
                <p class="post-excerpt">{post['excerpt']}</p>
                <div class="post-meta">
                    <span>📅 {post['date']}</span>
                    <span class="separator"></span>
                    <span>⚡ {post['reading_time']} min de leitura</span>
                </div>
            </div>
        </article>
        """

    def build_grid_html(posts_list):
        grid_items = []
        for post in posts_list:
            grid_items.append(f"""
            <article class="grid-post">
                <div class="grid-image-wrapper">
                    <img src="{post['image_path']}" alt="{post['title']}">
                </div>
                <div class="grid-info">
                    <a href="posts/{post['slug']}.html" class="grid-post-title">{post['title']}</a>
                    <p class="post-excerpt">{post['excerpt']}</p>
                    <div class="post-meta">
                        <span>📅 {post['date']}</span>
                        <span class="separator"></span>
                        <span>⚡ {post['reading_time']} min de leitura</span>
                    </div>
                </div>
            </article>
            """)
        return "\n".join(grid_items)

    # 1. Gerar index.html (Até 10 posts)
    if not posts:
        latest_hero = "<p style='text-align: center; color: var(--text-secondary);'>Nenhuma postagem encontrada ainda.</p>"
        posts_grid = ""
        bottom_nav = ""
    else:
        latest_hero = build_hero_html(posts[0])
        grid_posts = posts[1:10]  # post 1 ao 9 (máximo 10 total incluindo o hero)
        posts_grid = build_grid_html(grid_posts)
        
        if len(posts) > 10:
            bottom_nav = """
            <div class="archive-trigger">
                <a href="archive.html" class="btn-archive">Ver todas as postagens →</a>
            </div>
            """
        else:
            bottom_nav = ""

    index_html = template.replace("{{LIST_TITLE}}", "Últimas Postagens")
    index_html = index_html.replace("{{PAGE_TITLE}}", "Bifrost Tech News")
    index_html = index_html.replace("{{PAGE_SUBTITLE}}", "As principais novidades do mundo da tecnologia analisadas e detalhadas com apoio de IA.")
    index_html = index_html.replace("{{NAV_HOME_CLASS}}", "active")
    index_html = index_html.replace("{{NAV_ARCHIVE_CLASS}}", "")
    index_html = index_html.replace("{{LATEST_HERO}}", latest_hero)
    index_html = index_html.replace("{{POSTS_GRID}}", posts_grid)
    index_html = index_html.replace("{{BOTTOM_NAVIGATION}}", bottom_nav)

    with open(os.path.join(script_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # 2. Gerar archive.html (Todos os posts)
    if not posts:
        latest_hero = "<p style='text-align: center; color: var(--text-secondary);'>Nenhuma postagem encontrada ainda.</p>"
        posts_grid = ""
    else:
        latest_hero = build_hero_html(posts[0])
        grid_posts = posts[1:]  # Todos os posts restantes
        posts_grid = build_grid_html(grid_posts)

    archive_html = template.replace("{{LIST_TITLE}}", "Arquivo de Postagens")
    archive_html = archive_html.replace("{{PAGE_TITLE}}", "Todas as Postagens")
    archive_html = archive_html.replace("{{PAGE_SUBTITLE}}", "Explore todo o histórico de publicações do Bifrost Tech News.")
    archive_html = archive_html.replace("{{NAV_HOME_CLASS}}", "")
    archive_html = archive_html.replace("{{NAV_ARCHIVE_CLASS}}", "active")
    archive_html = archive_html.replace("{{LATEST_HERO}}", latest_hero)
    archive_html = archive_html.replace("{{POSTS_GRID}}", posts_grid)
    archive_html = archive_html.replace("{{BOTTOM_NAVIGATION}}", "")

    with open(os.path.join(script_dir, "archive.html"), "w", encoding="utf-8") as f:
        f.write(archive_html)

def main():
    try:
        print("1. Buscando o post mais relevante do Hacker News...")
        story = get_top_hacker_news_story()
        print(f"Encontrado: {story['title']}")
        print(f"Link Original: {story['link']}")

        slug = slugify(story['title'])
        
        # Garante que os diretórios necessários existam
        os.makedirs("posts", exist_ok=True)
        os.makedirs("posts/images", exist_ok=True)

        image_filename = f"{slug}.png"
        image_path = os.path.join("posts/images", image_filename)
        html_path = os.path.join("posts", f"{slug}.html")

        print("\n2. Gerando a versão adaptada em PT-BR com o Gemini 3.1 Flash-Lite...")
        post_text = generate_ptbr_content(story['title'])

        print(f"\n3. Gerando a imagem com o Nano Bana em {image_path}...")
        generate_mascot_image_via_interaction(story['title'], output_path=image_path)

        print(f"\n4. Renderizando o post em HTML em {html_path}...")
        reading_time, excerpt = render_html_post(
            title=story['title'],
            content_md=post_text,
            image_filename=image_filename,
            original_link=story['link'],
            hn_link=story['hn_link'],
            output_path=html_path
        )

        print("\n5. Atualizando metadados posts.json...")
        date_str = datetime.now().strftime("%d/%m/%Y")
        posts = update_posts_metadata(
            title=story['title'],
            date_str=date_str,
            slug=slug,
            image_filename=image_filename,
            original_link=story['link'],
            hn_link=story['hn_link'],
            reading_time=reading_time,
            excerpt=excerpt
        )

        print("\n6. Regenerando as páginas de listagem (index.html e archive.html)...")
        generate_list_pages(posts)

        print("\n--- PROCESSO CONCLUÍDO COM SUCESSO ---")
        print(f"📄 Novo Post: {html_path}")
        print(f"🖼️ Nova Imagem: {image_path}")
        print(f"🏠 Home Page atualizada com {min(10, len(posts))} postagens.")
        print("--------------------------------")

    except Exception as e:
        print(f"Ocorreu um erro na execução: {e}")

if __name__ == "__main__":
    main()