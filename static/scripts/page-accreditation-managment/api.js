class VoiseApi {
  baseUrl = "http://localhost:8000";

  async startSession(roomNumber) {
    try {
      const res = await fetch(`${this.baseUrl}/room/${roomNumber}/stages`, {
        method: "POST",
      });
      await res.json();
    } catch (error) {
      console.log(error);
    }
  }

  async patchSession(roomNumber, stage) {
    try {
      const res = await fetch(`${this.baseUrl}/room/${roomNumber}/stages`, {
        method: "PATCH",
        body: JSON.stringify({ stage }),
        headers: {
            'content-type': 'application/json'
        }
      });
      await res.json();
    } catch (error) {
      console.log(error);
    }
  }
}

export default new VoiseApi();
