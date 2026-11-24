# Entry point for everything heatmap related
heatmap_modules <- file.path(
  "R",
  "heatmap",
  c("map_base.R", "locations.R", "cells.R", "snapshot.R", "layers.R", "legend.R")
)
invisible(lapply(heatmap_modules, source, local = environment()))
