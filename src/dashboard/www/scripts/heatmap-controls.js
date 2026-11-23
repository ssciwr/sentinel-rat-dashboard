(function() {
  var currentMetric = "rodent";
  var advancedFilters = false;
  var activeHeatmapLayer = null;
  var pendingHeatmapView = null;
  var heatmapMessageHandlerRegistered = false;
  var sendInput = window.SentinelShiny.sendInput;

  /* AI-Generated */
  function queryAll(selector) {
    return Array.prototype.slice.call(document.querySelectorAll(selector));
  }
  /* AI-Generated */
  function invalidateHeatmapMap() {
    var finder = window.HTMLWidgets && window.HTMLWidgets.find;
    var widget = finder ? finder("#heatmap_map") : null;
    if (widget && typeof widget.getMap === "function") {
      widget.getMap().invalidateSize(false);
    }
  }
  /* AI-Generated
   * Returns the Leaflet map after the htmlwidget has finished binding.
   */
  function heatmapMap() {
    var finder = window.HTMLWidgets && window.HTMLWidgets.find;
    var widget = finder ? finder("#heatmap_map") : null;
    return widget && typeof widget.getMap === "function" ? widget.getMap() : null;
  }
  /* AI-Generated
   * Sends a generic browser drawing result without exposing implementation errors.
   */
  function reportMapRender(ok) {
    sendInput("heatmap_map_render_status", { ok: ok, nonce: Date.now() });
  }
  /* AI-Generated
   * Creates a text node so camera labels cannot be interpreted as HTML.
   */
  function cameraTooltip(text) {
    var tooltip = document.createElement("span");
    tooltip.textContent = text;
    return tooltip;
  }
  /* AI-Generated
   * Sends a selected camera identifier through the established Shiny input.
   */
  function selectCamera(camera) {
    sendInput("heatmap_map_shape_click", { id: camera.id, nonce: Date.now() });
  }
  /* AI-Generated
   * Adds one square cell and its activity indicator to a pending Leaflet layer.
   */
  function addHeatmapCell(layer, camera) {
    var cell = window.L.rectangle(
      [[camera.lat1, camera.lon1], [camera.lat2, camera.lon2]],
      {
        color: "transparent",
        fillColor: camera.fill_colour,
        fillOpacity: camera.fill_opacity,
        opacity: 0,
        weight: 0
      }
    );
    cell.bindTooltip(cameraTooltip(camera.tooltip), { sticky: true });
    cell.on("click", function() { selectCamera(camera); });
    layer.addLayer(cell);

    if (camera.has_activity) {
      if (pendingHeatmapView.metric === "predator") {
        return;
      }
      var plus = window.L.marker([camera.lat, camera.lon], {
        icon: window.L.divIcon({
          className: "heatmap-point-icon",
          html: "<span class='heatmap-point-plus'>+</span>",
          iconSize: [16, 16],
          iconAnchor: [8, 8]
        }),
        interactive: false
      });
      layer.addLayer(plus);
      return;
    }

    layer.addLayer(window.L.circleMarker([camera.lat, camera.lon], {
      radius: 4,
      fillColor: "#ffffff",
      fillOpacity: 0.12,
      color: "rgba(255, 255, 255, 0.86)",
      opacity: 0.45,
      weight: 1,
      interactive: false
    }));
  }
  /* AI-Generated
   * Adds one camera detail marker with dimensions for its activity or pressure view.
   */
  function addDetailMarker(layer, camera) {
    var showPressure = pendingHeatmapView.metric === "predator";
    var marker = window.L.marker([camera.lat, camera.lon], {
      icon: window.L.divIcon({
        className: "detail-activity-label",
        html: camera.detail_html,
        iconSize: showPressure ? [64, 36] : [60, 81],
        iconAnchor: showPressure ? [32, 18] : [30, 30]
      })
    });
    /* AI-Generated
     * Selects the camera represented by this detail marker.
     */
    marker.on("click", function() { selectCamera(camera); });
    layer.addLayer(marker);
  }
  /* AI-Generated
   * Replaces map layers only after the next complete layer has been built.
   */
  function renderHeatmapView() {
    var map = heatmapMap();
    if (!map || !pendingHeatmapView) {
      return;
    }
    try {
      var nextLayer = window.L.layerGroup();
      var cameras = pendingHeatmapView.cameras || [];
      var visibleCameras = cameras.filter(function(camera) {
        return map.getBounds().contains([camera.lat, camera.lon]);
      });
      var showDetail = pendingHeatmapView.show_cells && visibleCameras.length > 0 && visibleCameras.length <= 4;
      var legend = document.getElementById("heatmap_legend");
      if (legend) {
        legend.setAttribute("data-detail", String(showDetail));
      }
      if (pendingHeatmapView.show_cells) {
        if (showDetail) {
          visibleCameras.forEach(function(camera) { addDetailMarker(nextLayer, camera); });
        } else {
          cameras.forEach(function(camera) { addHeatmapCell(nextLayer, camera); });
        }
      }
      nextLayer.addTo(map);
      if (activeHeatmapLayer) {
        map.removeLayer(activeHeatmapLayer);
      }
      activeHeatmapLayer = nextLayer;
      reportMapRender(true);
    } catch (error) {
      console.error("Heatmap layer update failed.");
      reportMapRender(false);
    }
  }
  /* AI-Generated
   * Connects viewport changes to the latest R-supplied heatmap view.
   */
  function attachHeatmapRenderer() {
    var map = heatmapMap();
    if (!map) {
      window.setTimeout(attachHeatmapRenderer, 100);
      return;
    }
    if (!map._sentinelHeatmapRendererAttached) {
      map._sentinelHeatmapRendererAttached = true;
      map.on("moveend zoomend", renderHeatmapView);
      if (window.ResizeObserver) {
        map._sentinelResizeObserver = new ResizeObserver(invalidateHeatmapMap);
        map._sentinelResizeObserver.observe(map.getContainer());
      }
    }
    if (!map._sentinelHeatmapClientReady) {
      map._sentinelHeatmapClientReady = true;
      sendInput("heatmap_map_client_ready", { nonce: Date.now() });
    }
    renderHeatmapView();
  }
  /* AI-Generated
   * Registers the R message handler after Shiny has connected.
   */
  function registerHeatmapMessageHandler() {
    if (heatmapMessageHandlerRegistered || !window.Shiny || typeof Shiny.addCustomMessageHandler !== "function") {
      return;
    }
    Shiny.addCustomMessageHandler("heatmap-view", function(view) {
      pendingHeatmapView = view;
      renderHeatmapView();
    });
    heatmapMessageHandlerRegistered = true;
  }
  /* AI-Generated */
  function updateFilterPanels() {
    queryAll(".heatmap-filter-panel").forEach(function(panel) {
      var hidden = !advancedFilters && panel.getAttribute("data-filter-metric") !== currentMetric;
      panel.classList.toggle("is-hidden", hidden);
    });
    var toggleButton = document.getElementById("toggle_all_filters");
    if (toggleButton) {
      toggleButton.textContent = advancedFilters ? "Hide all filters" : "Show all filters";
      toggleButton.setAttribute("aria-expanded", String(advancedFilters));
    }
  }
  /* AI-Generated */
  function setAdvancedFilters(value) {
    advancedFilters = value === true;
    var checkbox = document.getElementById("show_all_filters");
    if (checkbox) {
      checkbox.checked = advancedFilters;
    }
    updateFilterPanels();
    sendInput("show_all_filters", advancedFilters);
  }
  /* AI-Generated */
  function setActiveHeatmapMetric(metric) {
    currentMetric = ["rodent", "total", "predator"].includes(metric) ? metric : "rodent";
    queryAll(".heatmap-view-button").forEach(function(button) {
      button.classList.toggle("is-active", button.getAttribute("data-heatmap-metric") === currentMetric);
      button.setAttribute("aria-pressed", String(button.getAttribute("data-heatmap-metric") === currentMetric));
    });
    updateFilterPanels();
    sendInput("heatmap_metric", currentMetric);
    window.setTimeout(invalidateHeatmapMap, 80);
  }
  /* AI-Generated */
  function syncInitialControls() {
    var activeButton = document.querySelector(".heatmap-view-button.is-active");
    var toggle = document.getElementById("show_all_filters");
    if (activeButton) {
      currentMetric = activeButton.getAttribute("data-heatmap-metric") || currentMetric;
    }
    advancedFilters = toggle ? toggle.checked : advancedFilters;
    setActiveHeatmapMetric(currentMetric);
    setAdvancedFilters(advancedFilters);
  }
  /* AI-Generated */
  function attachHeatmapControls() {
    if (document._sentinelHeatmapControls) {
      syncInitialControls();
      registerHeatmapMessageHandler();
      attachHeatmapRenderer();
      return;
    }
    document._sentinelHeatmapControls = true;
    document.addEventListener("click", function(event) {
      var canSearch = event.target && event.target.closest;
      var button = canSearch ? event.target.closest(".heatmap-view-button") : null;
      var marker = canSearch ? event.target.closest(".detail-activity-marker") : null;
      var allFiltersButton = canSearch ? event.target.closest("#toggle_all_filters") : null;
      if (allFiltersButton) {
        setAdvancedFilters(!advancedFilters);
      }
      if (button) {
        setActiveHeatmapMetric(button.getAttribute("data-heatmap-metric"));
      }
      if (marker) {
        sendInput("heatmap_detail_marker_click", { id: marker.getAttribute("data-camera-name"), nonce: Date.now() });
      }
    });
    document.addEventListener("change", function(event) {
      if (event.target && event.target.id === "show_all_filters") {
        setAdvancedFilters(event.target.checked);
      }
    });
    syncInitialControls();
    registerHeatmapMessageHandler();
    attachHeatmapRenderer();
  }

  window.SentinelHeatmapControls = { setMetric: setActiveHeatmapMetric, setAdvanced: setAdvancedFilters };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attachHeatmapControls);
  } else {
    attachHeatmapControls();
  }
  if (window.jQuery) {
    window.jQuery(document).on("shiny:connected shiny:bound shown.bs.tab", attachHeatmapControls);
  }
})();
