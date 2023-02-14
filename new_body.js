var contentZip = "{base64_zipfile}";

(function () {
  var urlParams = new URLSearchParams(window.location.search),
    path = urlParams.get("path") ? urlParams.get("path") : "",
    zip = new JSZip();

  if (-1 === path.indexOf(".html")) {
    path += "{start_page}";
  }

  zip
    .loadAsync(contentZip, {
      base64: true,
    })
    .then(
      function (zip) {
        if (!zip.file(path)) {
          alert("Could not find file in zipped content: " + path);
          return;
        }

        zip
          .file(path)
          .async("string")
          .then(async function (content) {
            var contentDom = document.createElement("html"),
              scripts = [];

            contentDom.innerHTML = content;

            // Import stylesheets
            contentDom
              .querySelectorAll("head link[rel=stylesheet]")
              .forEach(function (stylesheet) {
                window.document.head.append(document.importNode(stylesheet));
              });

            // Import scripts
            contentDom
              .querySelectorAll("script")
              .forEach(async function (oldScript) {
                var script = document.createElement("script");
                script.async = false;
                script.defer = false;
                if (oldScript.src) {
                  if (zip.file(oldScript.attributes.src.value)) {
                    // TODO not sure if this is helpful or needed
                    await zip
                      .file(oldScript.attributes.src.value)
                      .async("string")
                      .then(function (oldScriptContent) {
                        script.src =
                          "data:text/javascript;base64," +
                          btoa(oldScriptContent);
                      });
                  } else {
                    script.src = oldScript.src;
                  }
                } else {
                  // Turn inline scripts into data URIs to preserve loadging order
                  script.src =
                    "data:text/javascript;base64," + btoa(oldScript.innerHTML);
                }

                scripts.push(script);
                oldScript.remove();
              });

            // Import fonts
            for (i = 0; i < window.document.styleSheets.length; ++i) {
              let cssRules;
              try {
                cssRules = window.document.styleSheets[i].cssRules;
              } catch (e) {
                if (e instanceof DOMException) continue;
                throw e;
              }
              for (j = 0; j < cssRules.length; ++j) {
                rule = cssRules[j];
                if (rule instanceof CSSFontFaceRule) {
                  let src = rule.style.src;
                  // TODO maybe this can be done non-blocking
                  const replacements = await Promise.all(
                    Array.from(
                      src.matchAll(/(url\(")(.*?)("\))/g),
                      async function ([match, pre, name, post]) {
                        name = name.replace(/^(\.\/)+/g, "");
                        name = name + ".data-uri";
                        if (zip.file(name)) {
                          const fontContent = await zip
                            .file(name)
                            .async("string");
                          return [match, pre + fontContent + post];
                        } else {
                          return [match, match];
                        }
                      }
                    )
                  );

                  replacements.forEach(function ([oldText, newText]) {
                    src = src.replace(oldText, newText);
                  });

                  rule.style.setProperty("src", src);
                }
              }
            }

            // Replace body
            document.body.replaceWith(
              document.importNode(contentDom.querySelector("body"), true)
            );

            // Add imported scripts
            scripts.forEach(function (script) {
              document.body.append(script);
            });

            // Scroll to requested anchor
            if (window.location.hash != "") {
              element_to_scroll_to = document.getElementById(
                window.location.hash.slice(1)
              );
              element_to_scroll_to.scrollIntoView();
            }
          });
      },
      function () {
        alert("Cloud not open zipped content.");
      }
    );
})();
