#!/usr/bin/env Rscript
# P4-03 GeneNMF comparator on B regimes — native workflow only, execution + outputs.
#
# Frozen per PROTOCOL §5.5 (v1.2, pre-results): multiNMF k=4:10, nfeatures=2000
# (native default), seed 123, Seurat LogNormalize `data` slot, getMetaPrograms
# defaults (nMP=10, remove.empty=TRUE). No truth value is read here; truth meets
# the outputs later, in Python, as gene sets (marker sets are gene sets natively).
# Outputs are evidence inputs, never benchmark rows.
#
# Usage: Rscript docs/benchmarks/comparators/run_genenmf_B.R <in_dir> <out_dir>
suppressPackageStartupMessages({ library(Seurat); library(GeneNMF) })

args <- commandArgs(trailingOnly = TRUE)
in_dir <- args[1]; out_dir <- args[2]
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

t0 <- proc.time()
counts <- read.csv(file.path(in_dir, "counts_cells_x_genes.csv"), row.names = 1,
                   check.names = FALSE)
cells_meta <- read.csv(file.path(in_dir, "cells.csv"))
input_prov <- jsonlite::fromJSON(file.path(in_dir, "input_provenance.json"))

mat <- Matrix::Matrix(as.matrix(t(counts)), sparse = TRUE)
meta <- cells_meta[match(colnames(mat), cells_meta$cell), ]
rownames(meta) <- meta$cell

obj <- CreateSeuratObject(counts = mat, meta.data = data.frame(
  donor_id = meta$donor_id, row.names = rownames(meta)))
obj <- NormalizeData(obj, verbose = FALSE)

obj.list <- SplitObject(obj, split.by = "donor_id")
message(sprintf("donors: %d, cells: %d, genes: %d",
                length(obj.list), ncol(obj), nrow(obj)))

nmf.res <- multiNMF(obj.list, assay = "RNA", slot = "data", k = 4:10,
                    nfeatures = 2000, seed = 123)
mp <- getMetaPrograms(nmf.res)  # defaults: nMP=10, remove.empty=TRUE

saveRDS(nmf.res, file.path(out_dir, "nmf_models.rds"))
mp_genes <- mp[["metaprograms.genes"]]
mp_weights <- mp[["metaprograms.genes.weights"]]
write.csv(mp[["metaprograms.metrics"]], file.path(out_dir, "mp_metrics.csv"))
all_genes <- lapply(mp_genes, function(g) paste(g, collapse = ","))
write.csv(data.frame(metaprogram = names(mp_genes),
                     n_genes = lengths(mp_genes),
                     genes = unlist(all_genes)),
          file.path(out_dir, "mp_genes.csv"), row.names = FALSE)

elapsed <- (proc.time() - t0)[["elapsed"]]
prov <- list(
  genenmf_commit_sha = "59942b27c2cc2dbf55264b80b4ff26e3188cdf41",
  genenmf_version = as.character(utils::packageVersion("GeneNMF")),
  r_version = R.version.string,
  seed = 123, candidate_ranks = 4:10, nMP = "default(10)",
  normalization = "Seurat LogNormalize, data slot",
  hvg = "findHVG via multiNMF, nfeatures=2000(native default)",
  n_models = length(nmf.res),
  n_metaprograms = length(mp_genes),
  wall_seconds = unname(elapsed),
  input_manifest_hash = input_prov$dataset_manifest_hash
)
jsonlite::write_json(prov, file.path(out_dir, "provenance.json"),
                     auto_unbox = TRUE, pretty = TRUE)
message(sprintf("models: %d, meta-programs: %d, wall: %.1fs",
                length(nmf.res), length(mp_genes), elapsed))
