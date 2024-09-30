class Timer extends HTMLElement {
  static ATTRIBUTES = {
    TIME_STAMP: "time-stamp",
  };
  constructor() {
    super();
    this.rendered = false;
    this.currentDate = new Date();
    this.intervalId = null;
  }

  get initState() {
    return this.getAttribute(Timer.ATTRIBUTES.TIME_STAMP);
  }

  render() {
    if (!this.rendered) {
      const date = new Date(Number(this.initState) * 1000);
      this.currentDate = date;
      this.innerHTML = `<time style="font-size: 36px; font-weight: 900; color: ${this.getAttribute('color')};">${date.toLocaleString("ru-RU")}</time>`
      return;
    }
    const date = new Date(this.currentDate.getTime() + 1000);
    this.currentDate = date;
    this.innerHTML = `<time style="font-size: 36px; font-weight: 900; color: ${this.getAttribute('color')}">${date.toLocaleString("ru-RU")}</time>`;
  }

  connectedCallback() {
    if (!this.rendered) {
      this.render();
      this.rendered = true;
    }
    this.intervalId = setInterval(() => {
      this.render();
    }, 1000);
  }
  disconnectedCallback() {
    clearInterval(this.intervalId);
  }
}

export default Timer;
