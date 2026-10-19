#!/usr/bin/env Rscript
# 03c - fgsea cross-check for the D3 decision.
#
# Stage 5 GSEA (03b_enrichment.py) uses a size-bucketed permutation null in
# Python - approximate. This script re-ranks the SAME signed log2FC vectors
# (from <ACC>_DEG_full.csv) against the SAME gene-set collections (the GMTs
# exported by 03b under results/tables/gene_sets/) with R `fgsea` (exact,
# adaptive multilevel splitting) and writes side-by-side tables:
#
#   results/tables/gsea_<ACC>_<SRC>_fgsea.csv
#
# Interpretation is folded into the report/summary by 08_report.py (NES sign
# agreement + top-hit overlap). The Python tables remain the primary outputs;
# fgsea is a cross-check only.
#
# Run (Linux host): /path/to/Rscript scripts/03c_fgsea_crosscheck.R
suppressPackageStartupMessages({ library(yaml); library(data.table) })
if (requireNamespace("fgsea", quietly = TRUE)) {
  suppressPackageStartupMessages(library(fgsea))
} else {
  stop("fgsea not installed - install bioconductor-fgsea")
}
source(file.path(if (dir.exists("scripts")) "scripts" else ".", "R_utils.R"))
PROJ <- resolve_root()
cfg  <- load_config(PROJ)
TAB  <- file.path(PROJ, cfg$paths$tables)

cfge    <- cfg$deg$enrichment
min_size <- if (is.null(cfge$gsea_min_size)) 15 else cfge$gsea_min_size
max_size <- if (is.null(cfge$gsea_max_size)) 500 else cfge$gsea_max_size

sources <- unique(c("GO_BP", "GO-BP", "KEGG", "Reactome",
                    vapply(cfge$ontologies, function(s)
                      switch(toupper(s), BP = "GO_BP", `GO-BP` = "GO_BP",
                             REACTOME = "Reactome", toupper(s)), character(1))))
sources <- intersect(sources, c("GO_BP", "KEGG", "Reactome"))
accs <- c(cfg$cohorts$discovery$accession, cfg$cohorts$validation$accession)

cat("== 03c fgsea cross-check ==\n")
for (acc in accs) {
  full <- data.table::fread(file.path(TAB, paste0(acc, "_DEG_full.csv")))
  stats <- full$log2FoldChange
  names(stats) <- full$gene
  stats <- sort(stats[is.finite(stats)], decreasing = TRUE)
  cat("\n", acc, ": ranked", length(stats), "genes\n")
  for (src in sources) {
    gmt_f <- file.path(TAB, "gene_sets", paste0("gene_sets_", src, ".gmt"))
    if (!file.exists(gmt_f)) {
      cat("  [skip]", src, "- gmt not exported yet\n"); next
    }
    pathways <- fgsea::gmtPathways(gmt_f)
    fg <- fgsea::fgsea(pathways = pathways, stats = stats,
                       minSize = min_size, maxSize = max_size, nproc = 1)
    dt <- as.data.table(fg)[, .(term_id = pathway, set_size = size,
                                ES = ES, NES = NES,
                                pvalue = pval, padj = padj)]
    # carry display names from the Python tables when available
    py <- tryCatch(
      data.table::fread(file.path(TAB, paste0("gsea_", acc, "_", src, ".csv"))),
      error = function(e) NULL)
    if (!is.null(py)) dt$term_name <- py$term_name[match(dt$term_id, py$term_id)]
    out <- file.path(TAB, paste0("gsea_", acc, "_", src, "_fgsea.csv"))
    data.table::fwrite(dt, out)
    cat("  ", src, ":", nrow(dt), "sets ->", basename(out), "\n")
  }
}
cat("\n03c complete.\n")
