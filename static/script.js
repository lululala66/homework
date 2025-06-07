document.addEventListener("DOMContentLoaded", () => {
  // 站點搜尋自動完成功能（保留原本的）
  const input = document.getElementById("stationInput");
  const suggestionsBox = document.getElementById("suggestions");

  if (input) {
    input.addEventListener("input", () => {
      const query = input.value.trim();
      if (query.length === 0) {
        suggestionsBox.innerHTML = "";
        return;
      }

      fetch(`/search?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(results => {
          suggestionsBox.innerHTML = "";
          results.forEach(name => {
            const item = document.createElement("div");
            item.classList.add("suggestion-item");
            item.textContent = name;
            item.addEventListener("click", () => {
              input.value = name;
              suggestionsBox.innerHTML = "";
              document.querySelector("form").submit();
            });
            suggestionsBox.appendChild(item);
          });
        });
    });

    document.addEventListener("click", e => {
      if (!suggestionsBox.contains(e.target) && e.target !== input) {
        suggestionsBox.innerHTML = "";
      }
    });
  }

  // 👉 新增的頁籤切換功能
  const buttons = document.querySelectorAll(".tab-button");
  const contents = document.querySelectorAll(".tab-content");

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      contents.forEach(c => c.style.display = "none");

      btn.classList.add("active");
      const target = btn.getAttribute("data-target");
      document.getElementById(target).style.display = "block";
    });
  });
});
