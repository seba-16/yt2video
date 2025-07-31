from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title> YouTube Video Downloader</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { darkMode: 'class' }
  </script>
</head>
<body class="flex flex-col min-h-screen font-sans bg-gradient-to-br from-indigo-700 to-purple-700 text-white dark:from-gray-900 dark:to-black">

  <!-- Navbar -->
  <nav class="flex items-center justify-between p-4 bg-indigo-900 dark:bg-gray-800 shadow-md">
    <h1 class="text-2xl font-bold">YT2Video <span class="copyright text-white">©EXOR_SLAYS </span></h1>
    <button id="darkModeToggle" class="text-2xl">🌙</button>
  </nav>

  <!-- Main Section -->
  <main class="flex-grow flex flex-col items-center justify-center px-4">
    <div class="w-full max-w-xl p-6 bg-white/10 dark:bg-white/5 backdrop-blur-lg rounded-lg shadow-xl text-center">
      <h2 class="text-4xl font-extrabold mb-4">Download YouTube Videos</h2>
      <p class="text-lg mb-6">Paste a YouTube link below to get started</p>

      <form id="downloadForm" class="flex items-center bg-white dark:bg-gray-700 rounded-full p-2 shadow-md">
        <input
          id="urlInput"
          type="text"
          placeholder="Enter YouTube video URL"
          class="flex-grow px-4 py-2 text-black dark:text-white dark:bg-gray-700 rounded-l-full focus:outline-none"
        />
        <button
          type="submit"
          class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-r-full"
        >Search</button>
      </form>

      <div id="result" class="mt-6 text-sm text-white/90"></div>
      <div id="statusMessage" class="mt-4 text-yellow-300 font-semibold"></div>
    </div>
  </main>

  <!-- Footer -->
  <footer class="text-center text-sm py-4 text-white/80 dark:text-gray-300">
    © 2025 YT2Video. Built with ❤️ from EXOR_SLAYS
  </footer>

  <!-- Hidden iframe for download -->
  <iframe name="downloadFrame" style="display: none;"></iframe>

  <!-- JavaScript Section -->
  <script>
    const toggleBtn = document.getElementById("darkModeToggle");
    const html = document.documentElement;
    const form = document.getElementById("downloadForm");
    const input = document.getElementById("urlInput");
    const resultBox = document.getElementById("result");
    const statusBox = document.getElementById("statusMessage");

    toggleBtn.addEventListener("click", () => {
      html.classList.toggle("dark");
      toggleBtn.textContent = html.classList.contains("dark") ? "Light mode🌞" : "Dark mode🌙";
    });

    form.addEventListener("submit", function(e) {
      e.preventDefault();
      fetchVideo();
    });

    input.addEventListener("keypress", function(e) {
      if (e.key === "Enter") {
        e.preventDefault();
        fetchVideo();
      }
    });

    function fetchVideo() {
      const url = input.value.trim();
      if (!url) {
        alert("Please enter a YouTube URL");
        return;
      }

      resultBox.innerHTML = "Fetching available resolutions...";
      statusBox.innerHTML = "";

      fetch("/fetch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ url })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === "success") {
          let html = '<p class="mb-2 font-semibold text-green-300">Select a resolution to download:</p>';
          data.formats.forEach(f => {
            html += `
              <form method="POST" action="/download" target="downloadFrame" class="mb-2 resolution-form">
                <input type="hidden" name="url" value="${data.url}" />
                <input type="hidden" name="format_id" value="${f.format_id}" />
                <button class="bg-blue-500 hover:bg-blue-700 text-white py-1 px-4 rounded-full transition">
                  ${f.height}p (${f.ext})
                </button>
              </form>
            `;
          });
          resultBox.innerHTML = html;
        } else {
          resultBox.innerHTML = "❌ Could not fetch video info.";
        }
      })
      .catch(err => {
        console.error(err);
        resultBox.innerHTML = "⚠️ An error occurred while fetching the video.";
      });
    }

    // Intercept download form submission and show download status
    document.addEventListener("submit", function (e) {
      if (e.target.action.includes("/download")) {
        const btn = e.target.querySelector("button");
        if (btn) {
          btn.disabled = true;
          const originalText = btn.innerText;
          btn.innerText = "⏳ Please wait...";
          statusBox.innerHTML = "The video is getting ready to download...";

          setTimeout(() => {
            btn.innerText = "✅ Download will start";
            statusBox.innerHTML = "Download depends on your Internet and Resolution you choose";
            setTimeout(() => {
              btn.innerText = originalText;
              btn.disabled = false;
            }, 3000);
          }, 2000);
        }
      }
    }, true);
  </script>

</body>
</html>

"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/fetch", methods=["POST"])
def fetch():
    data = request.get_json()
    url = data.get("url")
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "forcejson": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {
                    "format_id": f["format_id"],
                    "height": f.get("height"),
                    "ext": f["ext"]
                }
                for f in info["formats"]
                if f.get("vcodec") != "none" and f["ext"] == "mp4" and f.get("height")
            ]
            # remove duplicate resolutions
            seen = set()
            unique_formats = []
            for f in sorted(formats, key=lambda x: -x["height"]):
                if f["height"] not in seen:
                    seen.add(f["height"])
                    unique_formats.append(f)

            return jsonify({
                "status": "success",
                "url": url,
                "formats": unique_formats
            })
    except Exception as e:
        print("Error fetching info:", str(e))
        return jsonify({"status": "error", "message": str(e)})

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")

    os.makedirs("downloads", exist_ok=True)

    # Extract video info to get the title
    info_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", f"video_{uuid.uuid4()}")
        safe_title = "".join(c if c.isalnum() or c in " -_." else "_" for c in title)
        filename = f"{safe_title}.mp4"
        filepath = os.path.join("downloads", filename)

    ydl_opts = {
        "format": f"{format_id}+bestaudio/best",
        "outtmpl": filepath,
        "quiet": True,
        "merge_output_format": "mp4"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return f"Download error: {str(e)}"


port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

