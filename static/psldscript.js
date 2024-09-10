const backToHome = document.querySelector("#back-to-home");
const sendButton = document.querySelector("#send-button");
const [ form ] = document.forms;
const inputSeries = form.querySelector('#series-number');
const keyboard = document.getElementById('keyboard-element');

let text123 = document.querySelector("text1234");

let attempts = 0;

backToHome.addEventListener("click", redirectToHome);
keyboard.addEventListener('key-clicked', (event) => {
  if (event.detail.keyValue === 'delete') {
    return inputSeries.value = inputSeries.value.slice(0, -1);
  }
  inputSeries.value+= event.detail.keyValue;
})

form.addEventListener('submit', (event) => {
  event.preventDefault();
  location.href = `/view-ticket/${inputSeries.value}`;
})

function resetLoadingState() {
  scanButton.disabled = false;
  scanButton.classList.remove("spin");
}

function redirectToHome() {
  location.href = "/touch";
}



function scan(obj) {
  // form submission starts
  // button is disabled
  scanButton.classList.add("spin");

  // This disables the whole form via the fieldset
  scanButton.disabled = true;
  //location.href = "/reg/" + "1234777888";

  function handleError() {
    attempts += 1;
    resetLoadingState();
    scanButton.textContent = "СКАНИРОВАТЬ ЕЩЁ РАЗ";
    document.getElementById("error_text").innerHTML =
      "<b>Ошибка при сканировании. Попробуйте ещё раз</b>";
    if (attempts >= 2) {
      redirectToHome();
    }
  }

  $.ajax({
    type: "GET",
    url: "http://127.0.0.1:8080",
    contentType: false,
    cache: false,
    processData: false,
    error: handleError,
    success: function (data) {
      if (data == "") {
        resetLoadingState();
      } else {
        console.log(data);
        if (data.slice(2, 5) == "RUS") {
          let series = data.slice(44, 48) + data[73] + data.slice(48, 54);
          location.href = "/reg/" + series;
          // 		console.log(series);
        } else {
          document.getElementById("error_text").innerHTML =
            "<b>Ваш паспорт не распознан. Обратитесь к администратору.</b>";
          resetLoadingState();
        }
      }
    },
  });
}
