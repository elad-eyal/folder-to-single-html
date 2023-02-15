import argparse
import base64
from functools import lru_cache
import io
import re
import sys
from zipfile import ZipFile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, TextIO

g_debug_zip: bool
g_source_directory: Path
g_output_filename: Path
g_start_page: Path


def parse_options():
    global g_debug_zip
    global g_source_directory
    global g_output_filename
    global g_start_page

    parser = argparse.ArgumentParser(
        prog="folder-to-single-html",
        description="Utility to convert a locally saved website into a single HTML file with similiar functionality and look"
        " and feel. This capability is useful for collecting multti-page HTML reports into a single, easy to browse file.",
        epilog="TODO",
    )
    parser.add_argument("source-directory", type=Path, default=".", help="TODO")
    parser.add_argument("--output-filename", "-o", type=Path, help="TODO")
    parser.add_argument(
        "--start-page", "-p", type=Path, default="index.html", help="TODO"
    )
    parser.add_argument(
        "--start-page-auto",
        "-P",
        action="store_true",
        help="Pick any HTML file as a start page",
    )
    parser.add_argument(
        "--debug-zip",
        action="store_true",
        help="For debugging, create a local copy of the embedded zip",
    )
    args = parser.parse_args()
    g_debug_zip = args.debug_zip
    g_source_directory = args.__dict__["source-directory"]
    g_output_filename = args.output_filename
    if args.start_page_auto:
        g_start_page = None
    else:
        g_start_page = args.start_page


def fail(reason: str):
    print(reason, file=sys.stderr)
    exit(6)


def get_all_filenames() -> List[Path]:
    root = g_source_directory
    for p in root.rglob("*"):
        if p.is_file:
            yield p.relative_to(root)


def rewrite_attributes(
    content: str,
    tag: str,
    attribute: str,
    current_path: Path,
    prefix: str = "",
    callback=None,
):
    def default_callback(matchobj: re.Match):
        pre, url, hash, post = matchobj.groups()
        if url == "" and hash.startswith("#"):
            return "".join(matchobj.groups())

        if "://" in url:
            return "".join(matchobj.groups())

        # Make f relative to root, instead of tthe currentt page's path
        f = str(current_path.parent / url)

        return f"{pre}{prefix}{f}{hash}{post}"

    content = re.sub(
        rf"(<{tag}\s[^>]*{attribute}=\")([^\"#]*)([^\"]*)(\"[^>]*>)",
        callback or default_callback,
        content,
        flags=re.IGNORECASE,
    )

    return content


def get_file_text(file: Path) -> str:
    return (g_source_directory / file).read_text()


@lru_cache(maxsize=None)
def get_file_as_uri_data(file: Path) -> str:
    suffix = file.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        mimetype = "image/jpeg"
    elif suffix == ".gif":
        mimetype = "image/gif"
    elif suffix == ".png":
        mimetype = "image/png"
    elif suffix == ".svg":
        mimetype = "image/svg+xml"
    elif suffix == ".css":
        mimetype = "text/css"
    else:
        fail(f"Problem converting {file.name}")

    t = (g_source_directory / file).read_bytes()

    return f"data:{mimetype};base64,{base64.b64encode(t).decode()}"


def outfile() -> TextIO:
    if g_output_filename is None:
        return sys.stdout
    return g_output_filename.open("w")


def main():
    global g_source_directory
    global g_output_filename
    global g_start_page

    parse_options()

    all_filenames = list(get_all_filenames())

    filenames_by_ext: Dict(List(Path)) = defaultdict(list)
    for f in all_filenames:
        filenames_by_ext[f.suffix].append(f)

    if not filenames_by_ext[".html"]:
        fail(f"There are no HTML files in the directory {g_source_directory}")

    if g_start_page is None:
        g_start_page = sorted(filenames_by_ext[".html"])[0]

    if g_start_page not in all_filenames:
        fail(f"There is no {g_start_page} in the directory {g_source_directory}.")

    files_to_inline = [
        fname
        for ext in (".css", ".gif", ".jpeg", ".jpg", ".png", ".svg")
        for fname in filenames_by_ext[ext]
    ]

    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, "w") as zip:
        for relpath in filenames_by_ext[".html"]:
            html = get_file_text(relpath)

            html = rewrite_attributes(html, "a", "href", relpath, "?path=")
            html = rewrite_attributes(html, "script", "src", relpath)
            # html = rewrite_attributes(html, 'link', 'href', relpath) - TODO

            def callback(m: re.Match):
                pre, url, _hash, post = m.groups()
                fname = relpath.parent / Path(url)
                if fname in files_to_inline:
                    return pre + get_file_as_uri_data(fname) + post
                return "".join(m.groups())

            html = rewrite_attributes(html, "img", "src", relpath, callback=callback)
            html = rewrite_attributes(html, "link", "href", relpath, callback=callback)

            zip.writestr(str(relpath), html)

    if g_debug_zip:
        Path("debug.zip").write_bytes(zip_buffer.getvalue())

    compiled = f"""
      <script type="text/javascript">
        { Path("./jszip/dist/jszip.min.js").read_text() }
        { ( Path("new_body.js")
            .read_text()
            .replace("{base64_zipfile}", base64.b64encode(zip_buffer.getvalue()).decode())
            .replace("{start_page}",g_start_page.name) )
        }
       </script>
       """

    with ZipFile(zip_buffer, "r") as zip:
        index_html = zip.read(g_start_page.name).decode()

    new_html_index_content = re.sub(
        r"<body[^>]*>(.*)</body>",
        lambda _: f"<body>{compiled}</body>",
        index_html,
        flags=re.IGNORECASE + re.DOTALL,
    )

    with outfile() as o:
        o.write(new_html_index_content)


if __name__ == "__main__":
    main()
