# criptonautas-featured-cover

[ENGLISH](README.md) | **ESPAÑOL**

Mantenido por Criptonautas. Sin afiliación ni respaldo de la Ghost Foundation ni de Civilized Discourse Construction Kit, Inc.

Genera una portada 1200×630 para los posts de Ghost sin imagen destacada y para los topics de wiki, curso y glosario de Discourse: una etiqueta y el título sobre la plantilla de Criptonautas de [brand-kit](https://github.com/somos-criptonautas/brand-kit). El título va en Inter Tight, hasta 3 líneas, cortado solo. Sale en PNG o WebP sin metadatos.

Es un servicio HTTP interno y chico. Lo llama n8n; nunca se expone a internet.

## Cómo encaja

1. Ghost dispara el webhook `post.published` hacia n8n.
2. El workflow de n8n `ghost-cover-add` lee el post. Si no tiene imagen destacada, le pide una portada a este servicio, la sube a Ghost y la pone como imagen destacada.
3. Discourse dispara su webhook de topics hacia n8n. El workflow `discourse-community-cover-add` toma los topics con el tag `wiki` o de las categorías Curso y Glosario cuyo primer post no tiene imagen, pide una portada con el estilo `community` y la agrega al final del primer post, que así pasa a ser la miniatura del topic.

## Instalar

GitHub Actions prueba la imagen y la publica en `ghcr.io/somos-criptonautas/criptonautas-featured-cover` en cada push a `main`. En el servidor no se construye nada.

Al lado del `docker-compose.yml` que corre n8n, crear el archivo del token:

```bash
umask 077; printf 'COVER_TOKEN=%s\n' "$(openssl rand -hex 32)" > cover.env
```

Pegar el servicio del [`docker-compose.yml`](docker-compose.yml) de este repo bajo `services:` en ese `docker-compose.yml`. Si el servicio de n8n tiene `networks:`, agregar las mismas redes a este servicio. Después:

```bash
docker compose up -d criptonautas-featured-cover
docker compose ps criptonautas-featured-cover   # tiene que decir "healthy"
```

En n8n, un nodo **HTTP Request**:

- Method `POST`, URL `http://criptonautas-featured-cover:8000/cover`
- Authentication: Header Auth, nombre `Authorization`, valor `Bearer <COVER_TOKEN>`
- Body JSON: `{"category": "...", "title": "...", "format": "webp"}`
- Response format: **File**. El nodo siguiente recibe la portada como binario.

## Actualizar

Push a `main`, esperar que pase el workflow Build y en el servidor:

```bash
docker compose pull criptonautas-featured-cover
docker compose up -d criptonautas-featured-cover
```

## API

- `POST /cover` con `Authorization: Bearer <COVER_TOKEN>` y JSON `{"category", "title", "format"}` → la imagen.
  - `format` es `png` (por defecto) o `webp`.
  - `style` es `article` (por defecto: pill `BLOG` y trama diagonal) o `community` (pill `COMUNIDAD` y cuadrícula). El pill va a la izquierda de la etiqueta, con la misma letra; si la etiqueta no entra al lado responde `422`.
  - Categoría hasta 30 caracteres, título hasta 140 y 3 líneas.
  - `Content-Disposition` lleva `cover.<format>`, así Ghost acepta la subida.
  - Errores: `401` token incorrecto, `400` sin `Content-Length`, `413` cuerpo de más de 4 KB, `422` con el motivo en texto (título largo, JSON inválido, un campo `image`).
- `GET /health` → `ok`.

El hueco de la ilustración acepta una imagen solo por línea de comandos:

```bash
python cover.py --category "Curso" --title "Qué es una wallet" --image ilus.png
# → covers/que-es-una-wallet-cover.png y .webp
```

## Ajustes de producción

El servicio no arranca sin un `COVER_TOKEN` de 32 caracteres o más. El bloque corre en solo lectura, con un usuario sin privilegios, sin capacidades de Linux, sin puertos publicados y con límites de 256 MB de memoria, medio CPU y 64 procesos. No registra títulos ni direcciones de clientes.

## Pruebas

```bash
pip install -r requirements.txt
python -m unittest discover tests                                                   # necesita Inter Tight instalada (assets/)
SERVICE_URL=http://127.0.0.1:8000 COVER_TOKEN=<token> python tests/service_check.py  # contra un contenedor corriendo
```

GitHub Actions corre las pruebas unitarias, construye la imagen, revisa el contenedor corriendo con los límites de producción y la publica solo si todo pasa.

## Créditos y licencia

Fuente: [Inter Tight](https://github.com/googlefonts/inter-tight) de Rasmus Andersson (SIL Open Font License, [`assets/OFL-inter-tight.txt`](assets/OFL-inter-tight.txt)). Logo: de [brand-kit](https://github.com/somos-criptonautas/brand-kit).

Código: [MIT](LICENSE). Texto del README: [CC BY-NC-SA 4.0](CC-BY-NC-SA-4.0.txt).
