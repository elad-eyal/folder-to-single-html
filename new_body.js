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
          .then(function (content) {
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
            contentDom.querySelectorAll("script").forEach(function (oldScript) {
              var script = document.createElement("script");
              script.async = false;
              script.defer = false;
              if (oldScript.src) {
                script.src = oldScript.src;
              } else {
                // Turn inline scripts into data URIs to preserve loadging order
                script.src =
                  "data:text/javascript;base64," + btoa(oldScript.innerHTML);
              }

              scripts.push(script);
              oldScript.remove();
            });

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
