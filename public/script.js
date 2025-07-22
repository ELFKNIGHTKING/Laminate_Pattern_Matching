document.addEventListener("DOMContentLoaded", () => {
  const imageInput = document.getElementById("imageInput");
  const searchBtn = document.getElementById("searchBtn");
  const previewContainer = document.getElementById("preview-container");
  const imagePreview = document.getElementById("imagePreview");
  const resultsContainer = document.getElementById("results-container");
  const resultsGrid = document.getElementById("results");

  let cropper = null;

  // Show preview when user selects a file
  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      previewContainer.classList.remove("hidden");

      if (cropper) cropper.destroy();
      cropper = new Cropper(imagePreview, {
        aspectRatio: NaN,
        viewMode: 1,
        background: false,
        movable: true,
        zoomable: false,
        scalable: false,
        wheelZoom: false,
        autoCropArea: 0.3,
      });
    };
    reader.readAsDataURL(file);

    // Clear previous results
    resultsGrid.innerHTML = "";
    resultsContainer.classList.add("hidden");
  });

  // On click, get cropped region, upload to /api/search and render results
  searchBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!cropper) {
      alert("Please select and crop an image first.");
      return;
    }

    const canvas = cropper.getCroppedCanvas({
      width: 512,
      height: 512,
      imageSmoothingQuality: "high",
    });

    if (!canvas) {
      alert("Please select a valid crop region.");
      return;
    }

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          alert("Failed to crop image.");
          return;
        }

        const formData = new FormData();
        formData.append("file", blob, "cropped.png");

        try {
          const endpoint = "/api/search";
          const resp = await fetch(endpoint, {
            method: "POST",
            body: formData,
          });

          if (!resp.ok) {
            const text = await resp.text();
            console.error("❌ HTTP error:", resp.status, resp.statusText, text);
            alert(`Search failed: ${resp.status} ${resp.statusText}`);
            return;
          }

          const data = await resp.json();
          const mainResults = data.filter((item) => item.segment_num === 0);

          resultsGrid.innerHTML = "";
          if (
            !Array.isArray(data) ||
            data.length === 0 ||
            mainResults.length === 0
          ) {
            resultsContainer.classList.remove("hidden");
            resultsGrid.innerHTML = `<div style="padding:1em;">No similar main images found.</div>`;
            return;
          }

          mainResults.forEach((item) => {
            const card = document.createElement("div");
            card.className = "result-card";
            card.innerHTML = `
              <img src="/uploads/${item.image_url}" alt="${item.name}" />
              <h4>${item.name ?? "N/A"}</h4>
              <p><b>Color:</b> ${item.color ?? "N/A"}</p>
              <p><b>Code:</b> ${item.code ?? "N/A"}</p>
              <p><b>Similarity:</b> ${(item.similarity * 100).toFixed(1)}%</p>
            `;
            card.addEventListener("click", () => {
              modalImage.src = `/uploads/${item.image_url}`;
              imageModal.classList.remove("hidden");
            });
            resultsGrid.appendChild(card);
          });

          resultsContainer.classList.remove("hidden");
        } catch (err) {
          console.error("💥 Unexpected error during search:", err);
          alert("Search failed with error—see console for details.");
        }
      },
      "image/png",
      0.95
    );
  });

  // Modal logic
  const imageModal = document.getElementById("imageModal");
  const modalImage = document.getElementById("modalImage");
  const closeBtn = document.querySelector(".modal .close");

  closeBtn.addEventListener("click", () => {
    imageModal.classList.add("hidden");
  });

  imageModal.addEventListener("click", (e) => {
    if (e.target === imageModal) {
      imageModal.classList.add("hidden");
    }
  });
});
