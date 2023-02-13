FROM python:3.10-slim-bullseye
COPY folder-to-single-html.py /folder-to-single-html.py
COPY new_body.js /new_body.js
COPY jszip/dist/jszip.min.js /jszip/dist/jszip.min.js
VOLUME [ "/in" ]
ENTRYPOINT [ "python3", "/folder-to-single-html.py", "/in" ]
