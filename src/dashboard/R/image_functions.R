# Support for inspector tool drawing bbxoes on frames etc

# These are mostly AI generated to iterate through images, render them, render BBOXes, with the rendered bbox positions checked.
camera_frame_image <- function(frame) {
  if ("image_path" %in% names(frame)) {
    image_path <- frame$image_path
    if (length(image_path) != 1 || is.na(image_path) || !file.exists(image_path)) return(NULL)
    return(base64enc::dataURI(file = image_path, mime = mime::guess_type(image_path)))
  }
  "camera-placeholder.png"
}

image_annotations <- function(selected_image_id, frame_detections) {
  image_detections <- frame_detections %>% filter(image_id == selected_image_id)
  if (nrow(image_detections) == 0) {
    return(list())
  }
  
  lapply(seq_len(nrow(image_detections)), function(index) {
    detection <- image_detections[index, ]
    x <- as.numeric(detection$x)
    y <- as.numeric(detection$y)
    width <- as.numeric(detection$width)
    height <- as.numeric(detection$height)
    
    list(
      id = detection$detection_id,
      bodies = list(list(
        purpose = "classifying",
        value = detection$label
      )),
      target = list(selector = list(
        type = "RECTANGLE",
        geometry = list(
          x = x,
          y = y,
          w = width,
          h = height,
          bounds = list(
            minX = x,
            minY = y,
            maxX = x + width,
            maxY = y + height
          )
        )
      )),
      properties = list(
        Species = detection$label,
        confidence = as.numeric(detection$confidence),
        origin = ifelse(detection$origin_type == "human", paste("Human:", detection$origin_name), detection$origin_name),
        status = ifelse(detection$origin_type == "human", "human-detected", "model-detected"),
        origin_type = detection$origin_type,
        origin_name = detection$origin_name
      )
    )
  })
}

preview_bbox_tags <- function(selected_image_id, frame_detections) {
  image_detections <- frame_detections %>% filter(image_id == selected_image_id)
  if (nrow(image_detections) == 0) {
    return(NULL)
  }
  
  lapply(seq_len(nrow(image_detections)), function(index) {
    detection <- image_detections[index, ]
    origin <- ifelse(
      detection$origin_type == "human",
      paste("Human:", detection$origin_name),
      detection$origin_name
    )
    tags$div(
      class = "preview-bbox",
      style = sprintf(
        "left: %.3f%%; top: %.3f%%; width: %.3f%%; height: %.3f%%;",
        detection$x / 960 * 100,
        detection$y / 540 * 100,
        detection$width / 960 * 100,
        detection$height / 540 * 100
      ),
      tags$span(class = "preview-bbox-label", paste(detection$label, origin, sep = " | "))
    )
  })
}

camera_frame_payload <- function(frame, annotations) {
  list(
    image_id = frame$image_id,
    camera_name = frame$camera_name,
    timestamp = format(frame$timestamp, "%Y-%m-%d %H:%M UTC"),
    image_url = camera_frame_image(frame),
    detection_count = frame$detection_count,
    annotations = annotations
  )
}

detection_count_label <- function(count) {
  label <- ifelse(count == 1, "detection", "detections")
  paste(count, label)
}
