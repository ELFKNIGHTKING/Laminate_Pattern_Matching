const form = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const laminateIdInput = document.getElementById("laminateIdInput");
const segmentNumInput = document.getElementById("segmentNumInput");
const nameInput = document.getElementById("nameInput");
const colorInput = document.getElementById("colorInput");
const codeInput = document.getElementById("codeInput");
const metadataInput = document.getElementById("metadataInput");
const previewImage = document.getElementById("previewImage");
const statusMessage = document.getElementById("statusMessage");

// Use a dynamic endpoint for flexibility
const endpoint = "http://192.168.2.92:8000/upload-laminate/";

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const file = fileInput.files[0];
  const laminate_id = laminateIdInput.value.trim();
  const segment_num = segmentNumInput.value.trim();
  const name = nameInput.value.trim();
  const color = colorInput.value.trim();
  const code = codeInput.value.trim();
  const metadata = metadataInput.value.trim();

  if (!file || !laminate_id || !segment_num || !name) {
    alert("Please fill all required fields.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("laminate_id", laminate_id);
  formData.append("segment_num", segment_num);
  formData.append("name", name);
  formData.append("color", color);
  formData.append("code", code);
  formData.append("metadata", metadata);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const result = await response.json();

    if (result.status === "success") {
      // Use absolute URL for image preview to ensure it works from anywhere
      previewImage.src = window.location.origin + result.image_url;
      previewImage.hidden = false;
      statusMessage.textContent = "Upload successful!";
      statusMessage.style.color = "green";
    } else if (result.status === "rejected") {
      previewImage.hidden = true;
      statusMessage.textContent = `Upload rejected: ${result.reason}`;
      statusMessage.style.color = "red";
    } else {
      throw new Error("Unexpected response");
    }
  } catch (err) {
    console.error(err);
    statusMessage.textContent = "Upload failed.";
    statusMessage.style.color = "red";
  }
});
