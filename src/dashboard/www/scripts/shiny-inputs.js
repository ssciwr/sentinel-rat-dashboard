window.SentinelShiny = {
  // helper to manage Shinys javascript object functions
  sendInput: function(inputName, inputValue) {
    if (!window.Shiny) {
      return;
    }
    if (typeof Shiny.setInputValue === "function") {
      Shiny.setInputValue(inputName, inputValue, { priority: "event" });
      return;
    }
    if (typeof Shiny.onInputChange === "function") {
      Shiny.onInputChange(inputName, inputValue);
      return;
    }
    console.warn("Shiny input API is unavailable.");
  }
};
