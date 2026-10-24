#!/usr/bin/env python

import re
import sys
import logging
import argparse
import html

from pathlib import Path
from datetime import date


logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent
POSTS_DIR = ROOT_DIR / 'posts'
HOMEPAGE_POSTS_COUNT = 5

POST_FILE_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})-.+\.html$')
TITLE_PATTERN = re.compile(r'<title>(.*?)</title>', re.S)
POST_BLOCK_PATTERN = re.compile(r'(<!-- posts:begin -->\n).*?(<!-- posts:end -->)', re.S)

POST_TEMPLATE = '''<!DOCTYPE html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="/css/style.css">
<title>{title}</title>
<h1>{title}</h1>
<p><a href="/">home</a> | <a href="/posts/">posts</a> | <a href="/about.html">about</a></p>
<p>{date}</p>
<hr>
<p>Start writing</p>
<hr>
<address>cr0w</address>
'''


def slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def iso_date(d: str) -> str:
    try:
        return date.fromisoformat(d).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError('Date is not in the YYYY-MM-DD format.')


def create_post(title: str, date: str, slug: str) -> None:
    slug = slugify(slug or title)

    if not slug:
        logger.error('Could not make a slug out of tile. pass slug with --slug')
        sys.exit('Post creation failed.')

    post = POSTS_DIR / f'{date}-{slug}.html'
    if post.exists():
        logger.error('Post already exists.')
        sys.exit('Post creation failed.')

    POSTS_DIR.mkdir(exist_ok=True)
    post.write_text(POST_TEMPLATE.format(title=html.escape(title), date=date), encoding='utf-8')

    logger.info(f'Post {post.relative_to(ROOT_DIR)} created.')
    logger.info('Edit body of post, then run ./build.py --build')


def read_post_list() -> (str, str, str):
    posts = []
    for path in POSTS_DIR.glob('*.html'):
        post_filename = POST_FILE_PATTERN.match(path.name)
        if not post_filename:
            continue

        date = post_filename.group(1)

        found_title = TITLE_PATTERN.search(path.read_text(encoding='utf-8'))
        if found_title:
            title = found_title.group(1).strip()
        else:
            title = path.stem
            logger.warning(f'No `<title>` in {path}')

        posts.append((path.name, date, title))

    posts.sort(reverse=True)
    return posts


def refresh_post_list(path, lines):
    old = path.read_text(encoding='utf-8')
    block = ''.join(line + '\n' for line in lines)

    new, count = POST_BLOCK_PATTERN.subn(lambda m: m.group(1) + block + m.group(2), old)
    if count != 1:
        logger.error('Post needs exactly one <!-- posts:begin --> / '
                     '<!-- posts:end --> pair, each on its own line.')
        sys.exit('Post list refreshing failed.')

    if new != old:
        path.write_text(new, encoding='utf-8')


def build():
    posts = read_post_list()
    lines = [f'{date}&nbsp;&nbsp;<a href="/posts/{name}">{title}</a><br>'
             for name, date, title in posts]

    refresh_post_list(ROOT_DIR / 'index.html', lines[:HOMEPAGE_POSTS_COUNT])
    refresh_post_list(POSTS_DIR / 'index.html', lines)

    logger.info(f'Built len({posts}) post')

def main(args) -> None:
    if args.create_post:
        if not args.title or not args.title.strip():
            logger.error('Flag --create-post needs --title')
            sys.exit('Operation failed.')
        create_post(args.title.strip(), args.date or date.today().isoformat(), args.slug)
    else:
        if args.title or args.date or args.slug:
            logger.error('Flags --title, --date and slug only go with --create-post')
            sys.exit('Operation failed')

        build()

    return None


if __name__ == '__main__':
    logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
            )

    parser = argparse.ArgumentParser(
        description="Create posts and refresh the post lists.",
        epilog='example: ./build.py --create-post --title "Hello again" && ./build.py --build')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create-post", action="store_true",
                      help="create a new post file (needs --title)")
    mode.add_argument("--build", action="store_true",
                      help="refresh the post lists in index.html and posts/index.html")
    parser.add_argument("--title", help="post title (with --create-post)")
    parser.add_argument("--date", type=iso_date, default=None,
                        help="post date as YYYY-MM-DD (default: today)")
    parser.add_argument("--slug", help="file name part (default: made from the title)")
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        sys.exit('Interrupted!')
