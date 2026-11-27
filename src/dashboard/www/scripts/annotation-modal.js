 /* Uses basic JS, no frameworks, to forward Annotorious annotation events to Shiny.
  *
  * This script runs with ui/templates/annotation_modal.html and relies on it heavily.
  * For example, ui.R fills the select box with species options for correction.
  *
  * This script supports (A) paginating through different detection images by asking Shiny for the next or previous frame
  * and (B) catching changes made with the Annotorious bbox tool, such as when boxes are updated.
  * It also supports deleting an existing bbox and creating new boxes through Annotorious.
  *
  * Yes, it is a bit annoying to have this JS here. It is a compromise. Annotorious already manages
  * the drawing, editing, and styling of boxes, so we only need to manage a basic state model and
  * communicate back to Shiny through SentinelShiny.sendInput. That keeps us from having to write our
  * own box editor, run a separate annotation web server, or adapt Plotly for bbox management.
  */
(function () {
	// Temporary basic state model
  var state = { annotator: null, frame: null, selected: null, annotations: {}, skipUpdateId: null };
  function byId(id) { return document.getElementById(id); }

  var sendInput = window.SentinelShiny.sendInput;
  
	function speciesOf(annotation) { return annotation.properties && annotation.properties.Species || ''; }
  
	function withSpecies(annotation, species) { return Object.assign({}, annotation, { properties: Object.assign({}, annotation.properties, { Species: species }) }); }
  
	function save() { if (state.annotator && state.frame) state.annotations[state.frame.image_id] = state.annotator.getAnnotations(); }
  function sendDetectionChange(eventType, annotation) {
    save();
    if (!window.Shiny || !state.frame) return;
    sendInput('detection_annotation_changed', {
      event_type: eventType,
      detection_id: annotation ? annotation.id : null,
      bbox: bboxCoordinates(annotation),
      annotations: state.annotations[state.frame.image_id],
      image_id: state.frame.image_id,
      species: annotation ? speciesOf(annotation) : ''
    });
  }

  // This BBOX helper function is AI generated
  function bboxCoordinates(annotation) {
    var geometry = annotation && annotation.target && annotation.target.selector && annotation.target.selector.geometry;
    if (!geometry) return null;
    var bounds = geometry.bounds;
    if (bounds) return { x0: bounds.minX, x1: bounds.maxX, y0: bounds.minY, y1: bounds.maxY };
    return { x0: geometry.x, x1: geometry.x + geometry.w, y0: geometry.y, y1: geometry.y + geometry.h };
  }
  function setSelection(annotations) {
    state.selected = annotations[0] || null;
    byId('annotation_species').value = state.selected ? speciesOf(state.selected) : '';
    byId('annotation_delete').disabled = !state.selected;
    byId('annotation_frame_id').textContent = state.selected ? state.selected.id : state.frame.image_id;
  }
  function initialise() {
    var image = byId('annotation_image');
    if (state.annotator || !window.Annotorious || !image || !state.frame) return;
    state.annotator = Annotorious.createImageAnnotator(image, { autoSave: true, drawingMode: 'drag', userSelectAction: 'EDIT' });
    state.annotator.setDrawingTool('rectangle');
    state.annotator.setAnnotations(state.annotations[state.frame.image_id] || state.frame.annotations || []);
    state.annotator.on('selectionChanged', setSelection);
    state.annotator.on('createAnnotation', function (annotation) {
      var next = withSpecies(annotation, byId('annotation_species').value);
      state.skipUpdateId = next.id;
      state.annotator.updateAnnotation(next);
      setSelection([next]);
      sendDetectionChange('bbox_created', next);
    });
    state.annotator.on('updateAnnotation', function (annotation) {
      if (annotation.id === state.skipUpdateId) {
        state.skipUpdateId = null;
        return;
      }
      setSelection([annotation]);
      sendDetectionChange('bbox_edited', annotation);
    });
    state.annotator.on('deleteAnnotation', function (annotation) { sendDetectionChange('bbox_deleted', annotation); });
  }
	// Fill the modal's existing HTML elements with the frame Shiny sent.
  function render(payload) {
    var image = byId('annotation_image');
    save();
    if (state.annotator) state.annotator.destroy();
    state.annotator = null;
    state.selected = null;
    state.frame = payload.image;
    state.annotations[state.frame.image_id] = state.frame.annotations || [];
	  // by ID is just getting each element below (HTML IDs not Shiny input$ or output$ IDs)
    byId('annotation_modal').classList.toggle('is-open', payload.open !== false);
    byId('annotation_title').textContent = state.frame.camera_name + ' | ' + state.frame.timestamp;
    byId('annotation_frame_id').textContent = state.frame.image_id;
    byId('annotation_prev').disabled = payload.total < 2;
    byId('annotation_next').disabled = payload.total < 2;
    image.onload = initialise; image.src = state.frame.image_url;
    if (image.complete) initialise();
  }
	// .selected contains the selected annotation. The species options come from ui.R.
  function updateSpecies() {
    if (!state.annotator || !state.selected) return;
    var next = withSpecies(state.selected, byId('annotation_species').value);
    state.skipUpdateId = next.id;
    state.annotator.updateAnnotation(next);
    setSelection([next]);
    sendDetectionChange('species_changed', next);
  }

  function deleteSelected() { if (state.annotator && state.selected) state.annotator.removeAnnotation(state.selected.id); }
  // Change the given annotation image.
	function step(amount) {
    sendDetectionChange('frame_saved', state.selected);
    sendInput('annotation_frame_step', { step: amount, nonce: Date.now() });
  }

  function close() {
    sendDetectionChange('frame_saved', state.selected);
    if (state.annotator) state.annotator.destroy(); state.annotator = null;
    byId('annotation_modal').classList.remove('is-open');
    sendInput('annotation_modal_closed', Date.now());
  }

  function attach() {
    byId('annotation_close').addEventListener('click', close);
    byId('annotation_prev').addEventListener('click', function () { step(-1); });
    byId('annotation_next').addEventListener('click', function () { step(1); });
    // Above is basic pagination
	  byId('annotation_species').addEventListener('change', updateSpecies);
    byId('annotation_delete').addEventListener('click', deleteSelected);
  }

  // restore existing saved annotations (For example, in the case of an error on saving your own edited bbox)
  function restoreAnnotations(payload) {
    state.annotations[payload.image_id] = payload.annotations || [];
    if (!state.frame || state.frame.image_id !== payload.image_id || !state.annotator) return;
    state.annotator.setAnnotations(state.annotations[payload.image_id]);
    setSelection([]);
  }
	// Wait for window.Shiny before registering message handlers, retrying every 50ms.
  function register() {
    if (window.Shiny) {
      Shiny.addCustomMessageHandler('open_annotation_modal', render);
      Shiny.addCustomMessageHandler('restore_annotations', restoreAnnotations);
    }
    else window.setTimeout(register, 50);
  }
// Once the page has loaded, attach the listeners for the modal controls.
	document.addEventListener('DOMContentLoaded', attach);
  register();
})();

// Shiny fills the modal template with species options and sends each camera frame, and Annotorious draws and edits the boxes in the browser.
// This script requests adjacent frames, forwards box and species changes through SentinelShiny.sendInput, and restores the last saved boxes when a save fails.
