// 簡易パスワードゲート(依存ゼロ)。
// 注意: これはカジュアルな抑止であり、本物のアクセス制御ではない。
// 認証を通すまで app.js を読み込まないが、データJSON自体は直URLで取得可能。
(function () {
  "use strict";
  var STORAGE_KEY = "epo_gate_ok_v1";
  // SHA-256( SALT + パスワード ) の16進。パスワード平文はソースに含めない。
  // 既定パスワードは別途案内。変更手順は README / scripts を参照。
  var SALT = "epo-league::";
  var EXPECTED_HASH =
    "2dcac8d94f72d07ef0786d60f6bb0f470f01f3cf40de1c681c8a633cc307464d";

  function loadApp() {
    var s = document.createElement("script");
    s.type = "module";
    s.src = "js/app.js?v=17"; // キャッシュバスター(JS更新時にバンプ)
    document.body.appendChild(s);
  }

  async function sha256Hex(text) {
    var buf = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(text)
    );
    return Array.prototype.map
      .call(new Uint8Array(buf), function (b) {
        return b.toString(16).padStart(2, "0");
      })
      .join("");
  }

  function showGate() {
    var ov = document.createElement("div");
    ov.id = "gate";
    ov.innerHTML =
      '<div class="gate-card">' +
      '<div class="gate-mark">EPO<b>°</b>LEAGUE</div>' +
      '<p class="gate-sub">閲覧にはパスワードが必要です</p>' +
      '<form id="gate-form">' +
      '<input id="gate-pw" type="password" autocomplete="current-password" ' +
      'placeholder="パスワード" autofocus />' +
      '<button type="submit">入場</button>' +
      "</form>" +
      '<p class="gate-err" id="gate-err"></p>' +
      "</div>";
    document.body.appendChild(ov);

    var form = ov.querySelector("#gate-form");
    var pw = ov.querySelector("#gate-pw");
    var err = ov.querySelector("#gate-err");

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      err.textContent = "";
      var hex = await sha256Hex(SALT + pw.value);
      if (hex === EXPECTED_HASH) {
        try {
          sessionStorage.setItem(STORAGE_KEY, "1");
        } catch (_) {}
        ov.remove();
        loadApp();
      } else {
        err.textContent = "パスワードが違います";
        pw.value = "";
        pw.focus();
      }
    });
  }

  // 既に当セッションで認証済みなら素通り。
  var ok = false;
  try {
    ok = sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch (_) {}

  if (ok) {
    loadApp();
  } else {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", showGate);
    } else {
      showGate();
    }
  }
})();
