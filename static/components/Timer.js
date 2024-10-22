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
      this.innerHTML = `<time style="font-size: 36px; font-weight: 900; color: ${this.getAttribute('color')};">${this.formattedDate}</time>`
      return;
    }
    const date = new Date(this.currentDate.getTime() + 1000);
    this.currentDate = date;
    const monthName = Timer.getMonthLabel(date.getMonth());
    
    const time = `${date.getHours()}:${date.getMinutes()}`;
    const textContent = `${date.getDate()} ${monthName} ${time}`
    this.innerHTML = `<time style="font-size: 36px; font-weight: 900; color: ${this.getAttribute('color')}">${this.formattedDate}</time>`;
  }

  get formattedDate() {
    const date = this.currentDate;
    const monthName = Timer.getMonthLabel(date.getMonth());
    
    const time = `${date.getHours()}:${date.getMinutes()}`;
    return `${date.getDate()} ${monthName} ${time}`
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

  static getMonthLabel(monthCode) {
    const months = {
      0: 'января',
      1: 'февраля',
      2: 'марта',
      3: 'апреля',
      4: 'мая',
      5: 'июня',
      6: 'июля',
      7: 'августа',
      8: 'сентября',
      9: 'октября',
      10: 'ноября',
      11: 'декабря'
    };
    return months[monthCode] ?? 'января';
  }
}

export default Timer;
