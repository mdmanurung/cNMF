#!/usr/bin/env Rscript
# P0-09 GeneNMF smoke adapter — native workflow only, execution check.
#
# Uses GeneNMF's own pipeline (multiNMF -> getMetaPrograms) exactly as its
# README/vignette prescribe. Its preprocessing (Seurat log-normalisation, own
# HVG selection, RcppML engine, specificity weighting, meta-program clustering)
# must NOT enter the cNMF baseline (IMPLEMENTATION_PROMPT.md:45). This script
# runs the comparator; it never writes into RESULTS.tsv/EXPERIMENTS.tsv.
#
# Choices recorded (smoke only, never tuned on a test set or on truth):
#   HVG: findHVG via multiNMF, nfeatures=100 (mirrors the SMOKE num_highvar_genes
#        budget; the simulator truth has K_true=3 but no truth value is read here)
#   ranks: k=2:4 (the SMOKE candidate grid in smoke_000m.yaml)
#   seed: 123 (GeneNMF default seed policy: single fixed seed)
#   nMP: default 10 with remove.empty=TRUE (no tuning)
#   normalization: Seurat LogNormalize, `data` slot (GeneNMF default slot)
#
# Usage:
#   Rscript docs/benchmarks/comparators/run_genenmf_smoke.R \
#     results/scratch/genenmf_smoke results/scratch/genenmf_smoke/out
suppressPackageStartupMessages({ library(Seurat); library(GeneNMF) })

args <- commandArgs(trailingOnly = TRUE)
in_dir <- args[1]; out_dir <- args[2]
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

t0 <- proc.time()
counts <- read.csv(file.path(in_dir, "counts_cells_x_genes.csv"), row.names = 1,
                   check.names = FALSE)
cells_meta <- read.csv(file.path(in_dir, "cells.csv"))
input_prov <- jsonlite::fromJSON(file.path(in_dir, "input_provenance.json"))

# Seurat convention is genes x cells; the CSV is cells x genes.
mat <- Matrix::Matrix(as.matrix(t(counts)), sparse = TRUE)
meta <- cells_meta[match(colnames(mat), cells_meta$cell), ]
rownames(meta) <- meta$cell

obj <- CreateSeuratObject(counts = mat, meta.data = data.frame(
  donor_id = meta$donor_id, row.names = rownames(meta)))
obj <- NormalizeData(obj, verbose = FALSE)

obj.list <- SplitObject(obj, split.by = "donor_id")
message(sprintf("donors: %d, cells: %d, genes: %d",
                length(obj.list), ncol(obj), nrow(obj)))

nmf.res <- multiNMF(obj.list, assay = "RNA", slot = "data", k = 2:4,
                    nfeatures = 100, seed = 123)
mp <- getMetaPrograms(nmf.res)  # defaults: nMP=10, remove.empty=TRUE

# Persist full loadings (genes x patterns per model) + meta-program outputs.
saveRDS(nmf.res, file.path(out_dir, "nmf_models.rds"))
mp_genes <- mp[["metaprograms.genes"]]
mp_weights <- mp[["metaprograms.genes.weights"]]
write.csv(mp[["metaprograms.metrics"]], file.path(out_dir, "mp_metrics.csv"))
for (i in seq_along(mp_weights)) {
  w <- mp_weights[[i]]
  write.csv(data.frame(gene = names(w), weight = as.numeric(w)),
            file.path(out_dir, sprintf("mp_%s_weights.csv", names(mp_weights)[i])),
            row.names = FALSE)
}

elapsed <- (proc.time() - t0)[["elapsed"]]
prov <- list(
  genenmf_commit_sha = "59942b27c2cc2dbf55264b80b4ff26e3188cdf41",
  genenmf_version = as.character(utils::packageVersion("GeneNMF")),
  r_version = R.version.string,
  seed = 123, candidate_ranks = c(2, 3, 4), nMP = "default(10)",
  normalization = "Seurat LogNormalize, data slot",
  hvg = "findHVG via multiNMF, nfeatures=100",
  n_models = length(nmf.res),
  wall_seconds = unname(elapsed),
  input_manifest_hash = input_prov$dataset_manifest_hash
)
jsonlite::write_json(prov, file.path(out_dir, "provenance.json"),
                     auto_unbox = TRUE, pretty = TRUE)
message(sprintf("models: %d, meta-programs: %d, wall: %.1fs",
                length(nmf.res), length(mp_genes), elapsed))
