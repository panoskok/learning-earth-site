# The Learning Earth: website

Static site for thelearningearth.com. Plain HTML, CSS and one small JS file. No framework, no database in this repo.

## Layout
- Built pages live at the repo root (`index.html`, `chi/`, `sources/`, ...). Plesk deploys the repo root to `httpdocs`.
- `_src/` holds the generator (`build.py`) and the article sources (`content/*.md`). It is blocked from public access by `.htaccess`.
- `_drafts/` holds pages that are built but not published (noindex, excluded from the sitemap).
- `subscribe.php`, `admin.php` and `subscribers.db` are deliberately NOT in this repo. They live on the server only, so a deploy never overwrites them.

## Publishing an article
1. Put the markdown in `_src/content/`.
2. Add or update its entry in `PAGES` in `_src/build.py` and set `status` to `published`.
3. Run `python3 _src/build.py` (needs Python with `markdown` and `Pillow`).
4. Commit and push. Plesk deploys automatically.
