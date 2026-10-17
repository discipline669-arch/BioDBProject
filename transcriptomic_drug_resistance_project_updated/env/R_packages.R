# R packages for the data / QC / DEG / enrichment track (Phase 1-3).
# Run on a host with Bioconductor available (the existing project ran this on Linux).
#
# Usage:
#   Rscript env/R_packages.R

cran <- c(
  "yaml", "ggplot2", "dplyr", "tidyr", "data.table", "Matrix",
  "pheatmap", "RColorBrewer", "ggrepel"
)

bioc <- c(
  "DESeq2", "limma", "edgeR", "clusterProfiler", "org.Hs.eg.db",
  "ReactomePA", "fgsea", "GEOquery", "EnhancedVolcano"
)

install_if_missing <- function(pkgs, repos = "https://cloud.r-project.org") {
  miss <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(miss)) install.packages(miss, repos = repos)
  invisible(miss)
}

install_if_missing(cran)

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", repos = "https://cloud.r-project.org")
}
miss_bioc <- bioc[!vapply(bioc, requireNamespace, logical(1), quietly = TRUE)]
if (length(miss_bioc)) BiocManager::install(miss_bioc, update = FALSE, ask = FALSE)

cat("R track packages installed (where possible).\n")
for (p in c(cran, bioc)) {
  cat(sprintf("%-20s %s\n", p, ifelse(requireNamespace(p, quietly = TRUE), "YES", "no")))
}
