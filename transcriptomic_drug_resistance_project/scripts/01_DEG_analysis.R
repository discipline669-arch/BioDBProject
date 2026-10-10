#!/usr/bin/env Rscript
# ============================================================
# BioDB Project — Member 2: DEG Analysis Pipeline
# Datasets: GSE303889 (SKOV-3) + GSE283381 (OVCAR5)
# ============================================================

suppressPackageStartupMessages({
  library(DESeq2)
  library(ggplot2)
  library(pheatmap)
  library(RColorBrewer)
  library(EnhancedVolcano)
  library(clusterProfiler)
  library(org.Hs.eg.db)
  library(VennDiagram)
  library(dplyr)
  library(tidyr)
})

set.seed(42)

# Resolve project root (works on the Linux host and this Windows machine)
resolve_proj <- function() {
  p <- Sys.getenv("BIODB_PROJ", unset = "")
  if (p != "" && dir.exists(p)) return(p)
  cands <- c("/home/nianderbrox/BioDB_Project",
             "E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project",
             getwd())
  cands[dir.exists(cands)][1]
}
PROJ <- resolve_proj()
cat("Project root:", PROJ, "\n")

DATA   <- file.path(PROJ, "data")
RESULTS <- file.path(PROJ, "results")

dir.create(file.path(RESULTS, "dataset1"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(RESULTS, "dataset2"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(RESULTS, "comparison"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(RESULTS, "enrichment"), recursive = TRUE, showWarnings = FALSE)

FDR_CUTOFF  <- 0.05
LFC_CUTOFF  <- 1
TOP_HEATMAP <- 50

# ============================================================
# HELPER FUNCTIONS
# ============================================================

run_deseq <- function(counts, coldata, contrast_name, results_dir) {
  cat("\n========== DESeq2:", contrast_name, "==========\n")

  dds <- DESeqDataSetFromMatrix(
    countData = counts,
    colData   = coldata,
    design    = ~ condition
  )

  dds$condition <- relevel(factor(dds$condition), ref = "Sensitive")
  keep <- rowSums(counts(dds)) >= 10
  dds <- dds[keep, ]
  cat("Genes after filtering:", nrow(dds), "\n")

  dds <- DESeq(dds)

  res <- results(dds, contrast = c("condition", "Resistant", "Sensitive"),
                 alpha = FDR_CUTOFF)
  res_df <- as.data.frame(res) %>%
    tibble::rownames_to_column("gene_id") %>%
    arrange(padj)

  write.csv(res_df, file.path(results_dir, "DEG_table_full.csv"), row.names = FALSE)

  sig_up   <- res_df %>% filter(padj < FDR_CUTOFF & log2FoldChange >  LFC_CUTOFF)
  sig_down <- res_df %>% filter(padj < FDR_CUTOFF & log2FoldChange < -LFC_CUTOFF)
  sig_all  <- res_df %>% filter(padj < FDR_CUTOFF & abs(log2FoldChange) > LFC_CUTOFF)

  cat("Up-regulated:  ", nrow(sig_up), "\n")
  cat("Down-regulated:", nrow(sig_down), "\n")
  cat("Total DEGs:    ", nrow(sig_all), "\n")

  write.csv(sig_all, file.path(results_dir, "DEGs_significant.csv"), row.names = FALSE)
  write.csv(sig_up,  file.path(results_dir, "DEGs_up.csv"), row.names = FALSE)
  write.csv(sig_down,file.path(results_dir, "DEGs_down.csv"), row.names = FALSE)

  # --- Volcano Plot ---
  volcano_df <- res_df %>%
    mutate(
      significance = case_when(
        padj < FDR_CUTOFF & log2FoldChange >  LFC_CUTOFF ~ "Up",
        padj < FDR_CUTOFF & log2FoldChange < -LFC_CUTOFF ~ "Down",
        TRUE ~ "NS"
      )
    )

  p_vol <- ggplot(volcano_df, aes(x = log2FoldChange, y = -log10(padj), color = significance)) +
    geom_point(alpha = 0.6, size = 1.2) +
    scale_color_manual(values = c("Up" = "#e41a1c", "Down" = "#377eb8", "NS" = "grey60"),
                       name = "Significance") +
    geom_vline(xintercept = c(-LFC_CUTOFF, LFC_CUTOFF), linetype = "dashed", color = "grey40") +
    geom_hline(yintercept = -log10(FDR_CUTOFF), linetype = "dashed", color = "grey40") +
    labs(title = paste("Volcano Plot —", contrast_name),
         x = expression(log[2]~Fold~Change),
         y = expression(-log[10]~adjusted~italic(P))) +
    theme_bw(base_size = 14) +
    theme(legend.position = "top")
  ggsave(file.path(results_dir, "volcano_plot.png"), p_vol, width = 8, height = 6, dpi = 300)

  # --- EnhancedVolcano ---
  gene_labels <- res_df %>%
    filter(padj < FDR_CUTOFF, abs(log2FoldChange) > LFC_CUTOFF) %>%
    arrange(padj) %>%
    head(20) %>%
    pull(gene_id)
  names(gene_labels) <- gene_labels

  png(file.path(results_dir, "enhanced_volcano.png"), width = 10, height = 8, units = "in", res = 300)
  EnhancedVolcano(res_df,
    lab = res_df$gene_id,
    x = "log2FoldChange", y = "padj",
    pCutoff = FDR_CUTOFF, FCcutoff = LFC_CUTOFF,
    title = paste("Enhanced Volcano —", contrast_name),
    pointSize = 2, labSize = 3.5,
    colAlpha = 0.6,
    legendPosition = "top",
    drawConnectors = TRUE, widthConnectors = 0.5, max.overlaps = 20)
  dev.off()

  # --- MA Plot ---
  png(file.path(results_dir, "MA_plot.png"), width = 8, height = 6, units = "in", res = 300)
  plotMA(res, main = paste("MA Plot —", contrast_name), ylim = c(-5, 5), alpha = FDR_CUTOFF)
  dev.off()

  # --- Heatmap of top DEGs ---
  if (nrow(sig_all) >= 2) {
    top_genes <- head(sig_all$gene_id, min(TOP_HEATMAP, nrow(sig_all)))
    mat <- counts(dds, normalized = TRUE)[top_genes, ]
    mat_scaled <- t(scale(t(log2(mat + 1))))
    anno_col <- data.frame(
      condition = coldata$condition,
      row.names = colnames(mat)
    )
    anno_colors <- list(condition = c("Sensitive" = "#4daf4a", "Resistant" = "#e41a1c"))

    png(file.path(results_dir, "heatmap_top_DEGs.png"),
        width = max(6, ncol(mat) * 0.8), height = max(8, length(top_genes) * 0.18),
        units = "in", res = 300)
    pheatmap(mat_scaled,
             annotation_col = anno_col, annotation_colors = anno_colors,
             cluster_rows = TRUE, cluster_cols = TRUE,
             show_rownames = (length(top_genes) <= 50),
             fontsize_row = 7,
             main = paste("Top", length(top_genes), "DEGs —", contrast_name),
             color = colorRampPalette(rev(brewer.pal(11, "RdBu")))(100),
             border_color = NA)
    dev.off()
  }

  return(list(dds = dds, res = res_df, sig_up = sig_up, sig_down = sig_down, sig_all = sig_all))
}

# ============================================================
# DATASET 1: GSE303889 — SKOV-3 (KDM5 / Cisplatin Resistance)
# ============================================================
cat("\n\n========================================\n")
cat("  DATASET 1: GSE303889 (SKOV-3)\n")
cat("========================================\n")

counts1_raw <- read.csv(file.path(DATA, "GSE303889", "GSE303889_rawcount.csv"),
                         check.names = FALSE)
cat("Raw dimensions:", dim(counts1_raw), "\n")

# Column mapping from SOFT file:
# dKO_NT_1/2/3 = Parental (Sensitive)
# CDDP_NT_1, CDDK_NT_2, CDDK_NT_3 = Resistant
# (CDDK_NT is a typo for CDDP_NT in the GEO submission)

coldata1 <- data.frame(
  sample    = c("Parental_rep1", "Parental_rep2", "Parental_rep3",
                "Resistant_rep1", "Resistant_rep2", "Resistant_rep3"),
  condition = c("Sensitive", "Sensitive", "Sensitive",
                "Resistant", "Resistant", "Resistant"),
  col_in_csv = c("dKO_NT_1", "dKO_NT_2", "dKO_NT_3",
                 "CDDP_NT_1", "CDDK_NT_2", "CDDK_NT_3"),
  row.names = c("dKO_NT_1", "dKO_NT_2", "dKO_NT_3",
                "CDDP_NT_1", "CDDK_NT_2", "CDDK_NT_3")
)

counts1 <- counts1_raw[, c("gene_id", "gene_name", coldata1$col_in_csv)]
counts_matrix1 <- as.matrix(counts1[, 3:8])
rownames(counts_matrix1) <- counts1$gene_id
colnames(counts_matrix1) <- rownames(coldata1)

write.csv(coldata1, file.path(DATA, "GSE303889", "coldata.csv"), row.names = FALSE)
write.csv(counts1, file.path(DATA, "GSE303889", "counts_filtered.csv"), row.names = FALSE)

ds1 <- run_deseq(counts_matrix1, coldata1, "SKOV-3 Resistant vs Sensitive (GSE303889)",
                 file.path(RESULTS, "dataset1"))

# ============================================================
# DATASET 2: GSE283381 — OVCAR5 (Cisplatin Resistance)
# ============================================================
cat("\n\n========================================\n")
cat("  DATASET 2: GSE283381 (OVCAR5)\n")
cat("========================================\n")

samples2 <- data.frame(
  sample    = c("OVCAR5_Sensitive_rep1", "OVCAR5_Sensitive_rep2", "OVCAR5_Sensitive_rep3",
                "OVCAR5_Resistant_rep1", "OVCAR5_Resistant_rep2", "OVCAR5_Resistant_rep3"),
  condition = c("Sensitive", "Sensitive", "Sensitive",
                "Resistant", "Resistant", "Resistant"),
  geo_id    = c("GSM8661174", "GSM8661175", "GSM8661176",
                "GSM8661180", "GSM8661181", "GSM8661182"),
  file_name = c("GSM8661174_OV5WTC1.count.out.txt.gz",
                "GSM8661175_OV5WTC2.count.out.txt.gz",
                "GSM8661176_OV5WTC3.count.out.txt.gz",
                "GSM8661180_OV5CRC1.count.out.txt.gz",
                "GSM8661181_OV5CRC2.count.out.txt.gz",
                
                "GSM8661182_OV5CRC3.count.out.txt.gz"),
  row.names = c("GSM8661174", "GSM8661175", "GSM8661176",
                "GSM8661180", "GSM8661181", "GSM8661182")
)

cat("Reading individual count files and merging...\n")
count_list <- list()
for (i in seq_len(nrow(samples2))) {
  f <- file.path(DATA, "GSE283381", samples2$file_name[i])
  d <- read.table(gzfile(f), header = FALSE, sep = "\t", stringsAsFactors = FALSE)
  colnames(d) <- c("gene_name", samples2$geo_id[i])
  d <- d[!grepl("^hsa-|^sno|^snR|^5S_rRNA|^5_8S|^7SK|^RN7SL|^Y_RNA|^U[0-9]", d$gene_name), ]
  count_list[[i]] <- d
}

counts2 <- count_list[[1]]
for (i in 2:length(count_list)) {
  counts2 <- merge(counts2, count_list[[i]], by = "gene_name", all = TRUE)
}
counts2[is.na(counts2)] <- 0

counts_matrix2 <- as.matrix(counts2[, -1])
rownames(counts_matrix2) <- counts2$gene_name
storage.mode(counts_matrix2) <- "integer"

cat("Dimensions after merge:", dim(counts_matrix2), "\n")

coldata2 <- data.frame(
  sample    = samples2$sample,
  condition = samples2$condition,
  row.names = samples2$geo_id
)

write.csv(coldata2, file.path(DATA, "GSE283381", "coldata.csv"), row.names = FALSE)
write.csv(counts2, file.path(DATA, "GSE283381", "counts_filtered.csv"), row.names = FALSE)

ds2 <- run_deseq(counts_matrix2, coldata2, "OVCAR5 Resistant vs Sensitive (GSE283381)",
                 file.path(RESULTS, "dataset2"))

# ============================================================
# CROSS-DATASET COMPARISON
# ============================================================
cat("\n\n========================================\n")
cat("  CROSS-DATASET COMPARISON\n")
cat("========================================\n")

# Use gene_name for comparison (convert dataset1 Ensembl IDs to gene names)
ds1_genes <- ds1$sig_all %>%
  left_join(counts1[, c("gene_id", "gene_name")], by = "gene_id") %>%
  filter(!is.na(gene_name))

ds2_genes <- ds2$sig_all %>%
  mutate(gene_name = gene_id)

shared_up   <- intersect(
  ds1_genes %>% filter(log2FoldChange > 0) %>% pull(gene_name),
  ds2_genes %>% filter(log2FoldChange > 0) %>% pull(gene_name)
)
shared_down <- intersect(
  ds1_genes %>% filter(log2FoldChange < 0) %>% pull(gene_name),
  ds2_genes %>% filter(log2FoldChange < 0) %>% pull(gene_name)
)
shared_all  <- intersect(ds1_genes$gene_name, ds2_genes$gene_name)

cat("Shared up-regulated:  ", length(shared_up), "\n")
cat("Shared down-regulated:", length(shared_down), "\n")
cat("Total shared DEGs:    ", length(shared_all), "\n")

shared_df <- data.frame(
  gene_name = shared_all,
  direction = ifelse(shared_all %in% shared_up, "Up",
                     ifelse(shared_all %in% shared_down, "Down", "Mixed"))
)

write.csv(shared_df, file.path(RESULTS, "comparison", "overlapping_DEGs.csv"), row.names = FALSE)
write.csv(ds1_genes, file.path(RESULTS, "comparison", "dataset1_annotated.csv"), row.names = FALSE)
write.csv(ds2_genes, file.path(RESULTS, "comparison", "dataset2_annotated.csv"), row.names = FALSE)

# --- Venn Diagram ---
png(file.path(RESULTS, "comparison", "venn_diagram.png"), width = 8, height = 6, units = "in", res = 300)
venn.plot <- venn.diagram(
  x = list(
    "GSE303889\n(SKOV-3)" = ds1_genes$gene_name,
    "GSE283381\n(OVCAR5)" = ds2_genes$gene_name
  ),
  category.names = c("GSE303889\n(SKOV-3)", "GSE283381\n(OVCAR5)"),
  filename = NULL,
  fill = c("#e41a1c", "#377eb8"),
  alpha = 0.4,
  cat.cex = 1.2,
  cex = 1.5,
  main = "Overlapping DEGs\n(Resistant vs Sensitive)"
)
grid.draw(venn.plot)
dev.off()

# --- Correlation of log2FC for shared genes ---
if (length(shared_all) > 2) {
  lfc_ds1 <- ds1_genes %>% filter(gene_name %in% shared_all) %>%
    select(gene_name, log2FC_ds1 = log2FoldChange)
  lfc_ds2 <- ds2_genes %>% filter(gene_name %in% shared_all) %>%
    select(gene_name, log2FC_ds2 = log2FoldChange)
  lfc_merged <- merge(lfc_ds1, lfc_ds2, by = "gene_name")

  cor_val <- cor(lfc_merged$log2FC_ds1, lfc_merged$log2FC_ds2, method = "spearman")
  cat("Spearman correlation of log2FC:", round(cor_val, 3), "\n")

  p_cor <- ggplot(lfc_merged, aes(x = log2FC_ds1, y = log2FC_ds2)) +
    geom_point(alpha = 0.6, color = "#6a3d9a", size = 2) +
    geom_smooth(method = "lm", se = TRUE, color = "#e31a1c", linetype = "dashed") +
    annotate("text", x = min(lfc_merged$log2FC_ds1), y = max(lfc_merged$log2FC_ds2),
             label = paste("Spearman r =", round(cor_val, 3)),
             hjust = 0, vjust = 1, size = 5, fontface = "italic") +
    labs(title = "log2FC Correlation — Shared DEGs",
         x = expression(log[2]~FC~(GSE303889~SKOV-3)),
         y = expression(log[2]~FC~(GSE283381~OVCAR5))) +
    theme_bw(base_size = 14)
  ggsave(file.path(RESULTS, "comparison", "lfc_correlation.png"), p_cor, width = 8, height = 6, dpi = 300)
}

# ============================================================
# FUNCTIONAL ENRICHMENT
# ============================================================
cat("\n\n========================================\n")
cat("  GO & KEGG ENRICHMENT\n")
cat("========================================\n")

run_enrichment <- function(gene_list, label, out_dir) {
  cat("\n--- Enrichment for:", label, "---\n")

  gene_df <- bitr(gene_list, fromType = "SYMBOL", toType = c("ENTREZID", "ENSEMBL"),
                   OrgDb = org.Hs.eg.db)
  if (nrow(gene_df) < 5) {
    cat("Too few mapped genes for enrichment. Skipping.\n")
    return(NULL)
  }
  entrez_ids <- unique(gene_df$ENTREZID)

  ego <- enrichGO(gene = entrez_ids, OrgDb = org.Hs.eg.db,
                  ont = "ALL", pAdjustMethod = "BH",
                  pvalueCutoff = 0.05, qvalueCutoff = 0.1,
                  readable = TRUE)

  if (!is.null(ego) && nrow(ego@result %>% filter(p.adjust < 0.05)) > 0) {
    write.csv(as.data.frame(ego), file.path(out_dir, paste0("GO_enrichment_", label, ".csv")),
              row.names = FALSE)

    p_go <- dotplot(ego, showCategory = 15, split = "ONTOLOGY") +
      facet_grid(ONTOLOGY ~ ., scales = "free_y") +
      ggtitle(paste("GO Enrichment —", label)) +
      theme(axis.text.y = element_text(size = 8))
    ggsave(file.path(out_dir, paste0("GO_dotplot_", label, ".png")), p_go,
           width = 10, height = 12, dpi = 300)
    cat("GO enrichment saved.\n")
  } else {
    cat("No significant GO terms found.\n")
  }

  ekegg <- enrichKEGG(gene = entrez_ids, organism = "hsa",
                       pvalueCutoff = 0.05, qvalueCutoff = 0.1)
  if (!is.null(ekegg) && nrow(ekegg@result %>% filter(p.adjust < 0.05)) > 0) {
    write.csv(as.data.frame(ekegg), file.path(out_dir, paste0("KEGG_enrichment_", label, ".csv")),
              row.names = FALSE)
    p_kegg <- dotplot(ekegg, showCategory = 15, title = paste("KEGG Pathways —", label))
    ggsave(file.path(out_dir, paste0("KEGG_dotplot_", label, ".png")), p_kegg,
           width = 10, height = 8, dpi = 300)
    cat("KEGG enrichment saved.\n")
  } else {
    cat("No significant KEGG pathways found.\n")
  }
}

# Shared DEGs enrichment
if (length(shared_all) > 0) {
  run_enrichment(shared_all, "Shared_DEGs", file.path(RESULTS, "enrichment"))
}

# Dataset-specific enrichments
if (nrow(ds1_genes) > 0) {
  run_enrichment(ds1_genes$gene_name, "Dataset1_SKOV3", file.path(RESULTS, "enrichment"))
}
if (nrow(ds2_genes) > 0) {
  run_enrichment(ds2_genes$gene_name, "Dataset2_OVCAR5", file.path(RESULTS, "enrichment"))
}

# Up- and down-regulated separately
if (length(shared_up) > 5) {
  run_enrichment(shared_up, "Shared_UP", file.path(RESULTS, "enrichment"))
}
if (length(shared_down) > 5) {
  run_enrichment(shared_down, "Shared_DOWN", file.path(RESULTS, "enrichment"))
}

cat("\n\n========================================\n")
cat("  PIPELINE COMPLETE\n")
cat("========================================\n")
cat("Results saved to:", RESULTS, "\n")
