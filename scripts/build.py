# build.py
import os
import shutil
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
DIST_DIR = "dist"


def build():
    """Builds the static HTML site from templates."""
    print("Starting build...")

    # 1. Clean and create the dist directory
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    # 2. Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    # 3. Find and render page templates (those not starting with '_')
    page_templates = [
        "index.html",
        "about.html",
        "movies.html",
        "persons.html",
        "person.html",
        "title.html",
        "genres.html",
        "top-rated.html",
        "short.html",
        "video.html",
        "videogame.html",
        "timeline.html",
        "tv.html",
        "search.html",
    ]

    print(f"Found page templates: {page_templates}")

    for template_name in page_templates:
        template = env.get_template(template_name)
        rendered_html = template.render()

        output_path = os.path.join(DIST_DIR, template_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        print(f"  - Rendered {template_name} -> {output_path}")

    # 4. Copy static assets if they exist
    if os.path.exists(STATIC_DIR):
        shutil.copytree(STATIC_DIR, os.path.join(DIST_DIR, "static"))
        print("Copied static assets.")
    else:
        # Create an empty static dir in dist so it can be served
        os.makedirs(os.path.join(DIST_DIR, "static"), exist_ok=True)

    print("\nBuild complete! Your static site is in the 'dist' directory.")


def main():
    build()


if __name__ == "__main__":
    main()
