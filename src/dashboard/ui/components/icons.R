
sentinel_icon <- function(name) {
  tags$svg(
    class = "bi", width = "1em", height = "1em", fill = "currentColor", viewBox = "0 0 16 16",
    `aria-hidden` = "true",
    tags$use(href = paste0("icons/bootstrap-icons.svg#", name))
  )
}
