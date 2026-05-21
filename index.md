<!--
  cache_key: 1638c1e9c055f4a9
  source_mtime: 1777345182.9810617
  generated_at: 2026-05-21T14:08:33
-->

# Project Index

## Project Overview

# Single-Cell Transcriptomic Profiling and Trajectory Inference

**Research Goal**  
This project aims to resolve cellular heterogeneity, define transcriptionally distinct cell populations, and reconstruct developmental trajectories from single-cell RNA sequencing (scRNA-seq) data. By mapping molecular states and lineage relationships, the analysis seeks to uncover the regulatory programs driving cell identity specification and dynamic state transitions within the sampled tissue.

**Analytical Methods**  
The workflow follows a standardized Scanpy-based scRNA-seq pipeline. Initial processing applies stringent quality control to remove low-quality cells and ambient RNA, followed by library size normalization and highly variable gene (HVG) selection to capture biologically relevant transcriptional variation. Dimensionality reduction via PCA and UMAP enables graph-based Leiden clustering to partition cells into coherent subpopulations. Cluster identities are resolved through differential expression analysis for robust marker discovery, while PAGA (Partition-based Graph Abstraction) is employed to infer pseudotemporal ordering and model lineage bifurcations across the cellular landscape.

**Figure Summary**  
The accompanying visualizations systematically document the analytical progression and highlight key biological insights. Initial QC plots (`violin_1_qc.png`, `scatter_2_qc.png`) confirm successful filtering of technical artifacts, while HVG dispersion and PCA variance plots (`filter_genes_dispersion_3_hvg.png`, `pca_variance_ratio_4_variance.png`) validate feature selection and optimal embedding dimensionality. The UMAP projection (`umap_5_leiden.png`) demonstrates clear cluster separation, which is biologically substantiated by ranked marker gene profiles (`rank_genes_groups_leiden_7_ranking.png`) and spatial expression overlays (`umap_8_markers.png`). Finally, the PAGA graph (`paga_9.png`) maps the inferred developmental continuum, revealing critical branching points and transitional states that govern cellular differentiation. Together, these outputs provide a high-resolution, trajectory-aware characterization of the tissue's cellular architecture.

## Images

| # | File | Path | Dimensions | Size |
|---|------|------|------------|------|
| 1 | filter_genes_dispersion_3_hvg.png | ../../pics/filter_genes_dispersion_3_hvg.png | 1059x565 | 79KB |
| 2 | paga_9.png | ../../pics/paga_9.png | 496x528 | 57KB |
| 3 | pca_variance_ratio_4_variance.png | ../../pics/pca_variance_ratio_4_variance.png | 561x605 | 43KB |
| 4 | rank_genes_groups_leiden_7_ranking.png | ../../pics/rank_genes_groups_leiden_7_ranking.png | 2008x1967 | 553KB |
| 5 | scatter_2_qc.png | ../../pics/scatter_2_qc.png | 624x600 | 217KB |
| 6 | umap_5_leiden.png | ../../pics/umap_5_leiden.png | 686x520 | 239KB |
| 7 | umap_8_markers.png | ../../pics/umap_8_markers.png | 2348x2614 | 3.9MB |
| 8 | violin_1_qc.png | ../../pics/violin_1_qc.png | 2254x716 | 480KB |

## Scripts

| # | File | Path | Language | Lines | Summary |
|---|------|------|----------|-------|---------|
| 1 | scanpy_ppl.py | ../../scripts/scanpy_ppl.py | py | 157 | import pandas as pd import scanpy as sc import numpy as np from pathlib import Path import argparse ... |

## Figure Captions

### Figure 1: 图 0. 单细胞转录组高变基因筛选散点图。

左图：X 轴表示基因平均表达量，Y 轴表示标准化离散度；右图：X 轴表示基因平均表达量，Y 轴表示未标准化离散度。

**Section Summary:** 本研究采用基于离散度的方法筛选高变基因，通过将基因按平均表达量分箱后计算标准化方差，以有效区分真实的生物学变异与测序技术噪声。分析共筛选出 2000 个高变基因，散点图中位于左上区域的基因表现出高离散度与低平均表达量的特征，通常对应于在特定细胞亚群中特异性高表达的调控因子或表面标志物。该筛选策略成功剔除了大量低信息量的持家基因与技术噪音，显著提升了数据信噪比。由此保留的高变基因集将作为核心特征输入后续的 PCA 降维与 Leiden 聚类算法，为精准解析细胞异质性、识别稀有细胞类型及推断发育轨迹奠定坚实的分子基础。

### Figure 2: 图 1. 基于 PAGA 算法的单细胞发育轨迹推断网络图。

图形采用无坐标轴的网络拓扑布局，节点与连线按力导向算法自动排布。

**Section Summary:** 本研究采用 PAGA（Partition-based Graph Abstraction）算法对 Leiden 聚类结果（分辨率设为 0.3，共划分 16 个细胞亚群）进行拓扑结构建模，旨在克服传统降维方法在连续发育过程中可能造成的流形断裂问题。图中节点代表独立的细胞聚类，连线粗细直观反映了基于单细胞转录组相似性计算出的状态转换概率，其中节点 0、2、13 等通过粗连线形成主干分支，提示存在明确的细胞分化主轴。该轨迹网络有效揭示了细胞群体从初始状态向终末分化状态的连续演变路径，为后续拟时序分析及关键调控基因的动态表达研究提供了可靠的拓扑学框架。

### Figure 3: 图 2. 主成分分析（PCA）方差贡献率分布图。

X 轴表示主成分排序，Y 轴表示对数尺度下的方差贡献率。

**Section Summary:** 本研究采用主成分分析（PCA）对高变基因表达矩阵进行降维，通过对数坐标展示各主成分的方差贡献率，以评估数据降维的有效性并确定后续分析的最佳维度。图中曲线呈现典型的“肘部”衰减趋势，前5个主成分（PC1-PC5）的方差贡献率显著高于后续成分，表明核心生物学变异高度集中于低维空间。该分布特征验证了单细胞转录组数据中存在明确的低维流形结构，前序主成分有效捕获了细胞亚群异质性与发育状态转换的关键信号。基于此方差衰减规律，分析流程选取前40个主成分构建细胞邻接图，在保留主要生物学差异的同时有效过滤了技术噪声，为后续Leiden聚类和PAGA轨迹推断奠定了稳健的数学基础。

### Figure 4: 图 3. 各 Leiden 聚类簇（Cluster 0-15）的差异表达基因（Marker Genes）排名图。

包含 16 个子图，分别对应 Cluster 0 至 15。X 轴表示基因排名，Y 轴表示差异表达评分（score）。

**Section Summary:** 本研究利用 Wilcoxon 秩和检验对 Leiden 聚类产生的 16 个细胞亚群进行差异表达分析，旨在鉴定各簇的特异性 Marker 基因。结果显示，每个亚群均具有独特的基因表达特征，例如 Cluster 0 显著富集 *Ghr* 和 *Sorbs1*，Cluster 3 高表达 *Dcn* 和 *Col1a2*（提示成纤维细胞或基质细胞特征），而 Cluster 1 则高表达 *Fl3a1* 等基因。各簇 Marker 基因的评分（Score）差异显著，部分簇（如 Cluster 3）的最高评分超过 350，表明其细胞群体具有高度均一且特异的转录组特征。这些 Marker 基因的鉴定为后续的细胞类型注释提供了关键依据，有助于解析样本中的细胞组成异质性及其潜在的生物学功能。

### Figure 5: 图 4. 单细胞转录组数据质控散点图，展示总读数、检出基因数与线粒体基因比例的关系。

X 轴表示总读数（total_counts），Y 轴表示检出基因数（n_genes_by_counts）。

**Section Summary:** 本研究采用 Scanpy 流程对单细胞转录组数据进行严格质控，通过散点图同步可视化总 UMI 计数、检出基因数与线粒体基因占比，旨在区分高质量完整细胞与低质量或破损细胞。图中细胞群体主要沿对角线分布，线粒体基因比例在低总读数区域显著升高，而高读数区域线粒体比例普遍维持在较低水平。结合预设的过滤阈值（线粒体比例 < 5% 且基因数 < 2500），该步骤有效剔除了因细胞膜破裂或凋亡导致线粒体 RNA 异常泄漏的异常细胞。此质控策略显著降低了技术噪音对下游分析的干扰，确保后续 PCA 降维、Leiden 聚类及 PAGA 轨迹推断能够精准捕捉真实的细胞亚群异质性与发育分化信号。

### Figure 6: 图 5. 基于 Leiden 算法的单细胞 UMAP 聚类分布图。

X 轴表示 UMAP1，Y 轴表示 UMAP2。

**Section Summary:** 本研究基于 PCA 降维后的前 40 个主成分，采用 Leiden 算法（分辨率参数设为 0.3）对单细胞转录组数据进行无监督聚类，并通过 UMAP 进行二维可视化以保留细胞间的全局与局部拓扑结构。结果显示共鉴定出 16 个转录组特征各异的细胞亚群（Cluster 0-15），各群体在降维空间中呈现清晰的边界与良好的空间分离度，表明样本内存在显著的细胞异质性。这种明确的聚类结构有效反映了不同细胞类型或发育状态的转录差异，为后续特异性 Marker 基因的筛选提供了可靠的群体划分依据。同时，清晰的亚群分布也为 PAGA 轨迹推断奠定了拓扑基础，有助于进一步解析细胞分化路径与状态转换的动态过程。

### Figure 7: 图 6. 单细胞 UMAP 聚类分布及关键 Marker 基因表达模式图。

X 轴表示 UMAP1，Y 轴表示 UMAP2。上排 16 个子图分别展示不同 Marker 基因；底部子图展示 Leiden 聚类结果。

**Section Summary:** 本研究利用 Scanpy 流程对单细胞数据进行降维聚类，并通过 Wilcoxon 秩和检验鉴定各 Leiden 亚群（Resolution=0.3）的特异性 Marker 基因。UMAP 可视化结果显示，数据被清晰划分为 16 个独立的细胞簇（Cluster 0-15），且不同簇之间具有明显的空间界限。基因表达图谱揭示了高度的细胞异质性：例如，*Ghr*、*F13a1* 和 *Ctcfls* 在特定簇（如 Cluster 0）中呈现高丰度特异性表达，提示该群体可能具有特定的内分泌或结构功能；而 *Actb* 作为管家基因在各群中广泛表达。此外，*Ighm* 和 *Lyz2* 的局灶性高表达暗示了免疫细胞（如 B 细胞或巨噬细胞）的存在。这些 Marker 基因的特异性分布不仅验证了聚类结果的生物学合理性，也为后续解析细胞发育轨迹和功能状态提供了关键的分子标签。

### Figure 8: 图 7. 单细胞转录组数据质控（QC）指标分布小提琴图。

左、中、右三图分别展示每个细胞的检测基因数、总测序读数及线粒体基因占比，Y 轴表示对应指标的数值。

**Section Summary:** 本研究采用 Scanpy 流程对原始单细胞数据进行质控，通过计算每个细胞的检测基因数、总 UMI 计数及线粒体基因占比评估数据质量，旨在剔除裂解细胞、双细胞及高线粒体含量的凋亡细胞。小提琴图显示，绝大多数细胞的基因数集中在 500 至 2500 之间，总读数呈典型右偏分布，而线粒体基因占比主要聚集在 5% 以下，仅极少数细胞呈现异常高值。基于该分布特征，流程设定了严格过滤阈值（MT < 5%，Genes < 2500），有效去除了技术噪音与低活性细胞。高质量的细胞子集显著降低了技术异质性对后续降维聚类的干扰，为高变基因筛选、Leiden 聚类及 PAGA 轨迹推断奠定了可靠基础，确保下游鉴定的细胞亚群与发育状态转换真实反映生物学差异。
