import ProgressBar from "../../components/ProgressBar.js";

function redirectToHome() {
  location.href = "/touch";
}
const backToHome = document.querySelector("#back-to-home");
const printTicketBtn = document.querySelector("#print-ticket");

backToHome.addEventListener("click", redirectToHome);
printTicketBtn.addEventListener("click", () => {
  location.href = printTicketBtn.dataset.redirectUrl;
});

function setTimer() {
  let restSeconds = 10;

  const interval = setInterval(() => {
    if (restSeconds > 0) {
      restSeconds -= 1;
    } else {
      return clearInterval(interval);
    }
    const progress = (10 - restSeconds) * 10;
    progressBar.progress = progress;
  }, 1000);
}

customElements.define("progress-bar-element", ProgressBar);

const progressBar = document.querySelector("#progress-bar");

progressBar.addEventListener("mounted", () => {
  setTimer();
});

progressBar.addEventListener(ProgressBar.EMITS.FINISH, () => {
  setTimeout(() => {
    //redirectToHome();
    console.log("redirected");
  }, 1000);
});
