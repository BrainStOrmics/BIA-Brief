<!--
  cache_key: 1638c1e9c055f4a9
  source_mtime: 1777345182.9810617
  generated_at: 2026-05-21T16:49:10
-->

# Project Index

## Project Overview

This single-cell transcriptomic analysis applied a standard Scanpy workflow to dissect cellular heterogeneity and developmental relationships. After stringent quality control filtering of genes and cells, counts were normalized and highly variable genes were identified based on dispersion. Dimensionality reduction via principal component analysis captured the major transcriptional variance, and the neighborhood graph was visualized using UMAP. Unsupervised Leiden clustering resolved transcriptionally distinct cell groups, whose discriminating marker genes were ranked by differential expression and projected onto the UMAP embedding. Finally, trajectory inference through PAGA reconstructed a graph of connectivity between clusters, highlighting potential differentiation lineages and transitional states. The output figures confirm effective data cleaning and subsetting, clear separation of Leiden clusters on UMAP, robust marker gene specificity across populations, and a structured developmental continuum with branching inferred from the PAGA topology.

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

### Figure 1: 图 0. 单细胞转录组高变基因筛选分布图。

左图 X 轴表示基因平均表达量，Y 轴表示标准化后的基因离散度；右图 X 轴表示基因平均表达量，Y 轴表示未标准化的基因离散度。

**Section Summary:** 本研究采用 Scanpy 内置的高变基因筛选算法，通过将基因按平均表达量分箱并计算标准化离散度，有效区分生物学变异与技术噪声，最终筛选出 2000 个高变基因用于下游分析。散点图显示，被标记为高变基因的位点在低至中等表达区间呈现出显著高于背景噪声的离散度，而绝大多数基因的离散度随表达量升高而趋于平稳。该筛选策略精准捕获了驱动细胞异质性的关键转录特征，去除了大量低信息量的管家基因与技术噪音，为后续 PCA 降维、Leiden 聚类及细胞发育轨迹推断奠定了可靠的分子基础，确保细胞亚群划分与状态转换分析的特异性与准确性。

### Figure 2: 图 1. 基于 PAGA 算法的单细胞发育轨迹推断网络图。

无坐标轴，展示基于 Leiden 聚类的细胞状态拓扑网络布局。

**Section Summary:** 本研究采用 PAGA（Partition-based Graph Abstraction）算法构建细胞状态转换的拓扑网络，该方法通过将 Leiden 聚类结果抽象为图节点，有效克服了传统降维方法在刻画连续分化过程时的离散化局限，特别适用于解析具有多分支命运的发育轨迹。网络图共包含 16 个聚类簇（编号 0-15），节点大小反映各簇细胞丰度，连线粗细表征簇间转录组相似性与转换概率；其中簇 0 作为核心枢纽与多个下游簇（如 2、5、13）相连，而簇 1、6、7、8、9 等形成紧密连接的子网络，提示存在高度相关的细胞亚群或过渡态。该拓扑结构清晰揭示了细胞群体从初始状态向特定谱系分化的潜在路径与分支节点，为后续拟时序分析、关键调控基因鉴定及细胞命运决定机制的深入解析提供了可靠的拓扑学框架。

### Figure 3: 图 2. 单细胞转录组 PCA 主成分方差贡献率分布图。

X 轴表示主成分排序（ranking），Y 轴表示对数刻度下的方差贡献率（variance ratio）。

**Section Summary:** 本研究采用主成分分析（PCA）对高变基因表达矩阵进行降维，通过对数刻度展示前50个主成分的方差贡献率，以评估数据内在结构并确定后续分析的有效维度。图中显示前5个主成分（PC1至PC5）的方差贡献率显著高于后续成分，呈现典型的陡峭下降趋势，表明细胞间的主要转录异质性高度集中于少数正交维度；随着排序增加，方差贡献率逐渐趋于平缓，提示后续主成分主要捕获技术噪声或微弱生物学信号。该分布特征验证了降维策略的合理性，表明保留前10至20个主成分即可充分表征核心生物学变异。此低维特征空间为后续构建细胞邻接网络、执行Leiden聚类及PAGA发育轨迹推断奠定了稳健的数学基础，确保下游分析能够精准解析细胞亚群划分与状态转换机制。

### Figure 4: 图 3. 单细胞聚类簇 Marker 基因排名图，展示 Cluster 0-15 的特异性高表达基因。

包含 16 个子图，分别对应 Cluster 0 至 15 与其余细胞的对比；X 轴表示基因排名，Y 轴表示差异表达得分。

**Section Summary:** 本研究采用 Wilcoxon 秩和检验 (`sc.tl.rank_genes_groups`) 对 Leiden 聚类结果进行 Marker 基因鉴定，旨在寻找每个细胞亚群的特异性标志物。图中展示了 Cluster 0 至 15 共 16 个亚群的差异基因排名情况，X 轴为基因排名，Y 轴为统计得分（score），得分越高表明该基因在对应簇中的表达特异性越强。例如，Cluster 0 高表达 *Ghr* 和 *Sorbs1*，Cluster 1 高表达 *Fl3a1* 和 *Selenop*，Cluster 3 高表达 *Dcn* 和 *Fst1*。这些高得分基因不仅验证了聚类的有效性，区分了不同的细胞群体，也为后续基于已知 Marker 数据库进行细胞类型注释提供了关键的分子依据，揭示了样本中复杂的细胞异质性。

### Figure 5: 图 4. 单细胞转录组数据质控散点图，展示测序深度、检测基因数与线粒体基因比例的关系。

X 轴表示总测序读数（total_counts），Y 轴表示检测到的基因数（n_genes_by_counts）。

**Section Summary:** 本研究采用 Scanpy 流程对单细胞转录组数据进行严格质控，通过计算每个细胞的总 UMI 数、检测基因数及线粒体基因占比，评估细胞完整性与测序质量。该步骤旨在识别并剔除因细胞破裂或低质量捕获导致的高线粒体污染细胞，确保下游分析基于高质量转录组数据。散点图显示细胞群体沿对角线分布，表明总读数与检测基因数呈正相关；颜色梯度反映线粒体基因比例变化，绝大多数细胞线粒体占比集中在 0-5% 区间，符合预设过滤阈值。线粒体基因异常高表达通常提示细胞膜破损或处于凋亡应激状态，严格质控可有效排除技术噪音与死亡细胞干扰。保留的高质量细胞群为后续高变基因筛选、降维聚类及发育轨迹推断奠定了可靠的数据基础，保障了细胞亚群划分与生物学结论的准确性。

### Figure 6: 图 5. 基于 Leiden 算法的单细胞 UMAP 聚类分布图。

X 轴表示 UMAP1 坐标，Y 轴表示 UMAP2 坐标。

**Section Summary:** 本研究基于 PCA 降维后的前 40 个主成分，采用 Leiden 算法（分辨率参数设为 0.3）对单细胞转录组数据进行无监督聚类，并通过 UMAP 进行二维可视化以保留细胞间的局部与全局拓扑结构。结果显示共鉴定出 16 个转录组特征各异的细胞亚群（Cluster 0-15），各群体在降维空间中呈现清晰的边界与良好的分离度，部分边缘簇的弥散分布提示可能存在过渡态或稀有细胞类型。该聚类结果有效揭示了样本内高度的细胞异质性，为后续差异表达分析提供了可靠的群体划分依据。明确的亚群结构不仅有助于精准鉴定各细胞类型的特异性标志物，也为 PAGA 轨迹推断奠定了拓扑基础，从而能够系统解析细胞分化路径与发育状态转换的动态过程。

### Figure 7: 图 6. 单细胞 UMAP 聚类及各亚群 Top1 Marker 基因表达分布图。

上排至下排展示各基因表达分布，左下角展示 Leiden 聚类分组。

**Section Summary:** 本研究基于 Scanpy 流程对单细胞转录组数据执行 Leiden 聚类（分辨率设为 0.3），共划分出 16 个细胞亚群，并采用 Wilcoxon 秩和检验提取各群组的 Top1 差异基因进行 UMAP 空间映射。可视化结果显示，Ghr、F13a1、Lyz2 及 Actb 等标志物在特定聚类区域内呈现高度局域化富集，表达梯度清晰揭示了转录活性的空间异质性，有效验证了降维聚类算法在解析细胞群体结构上的可靠性。这些特异性基因广泛参与代谢调控、先天免疫应答及细胞骨架维持等核心生理过程，表明样本内存在功能高度特化的细胞亚型。该分子特征图谱不仅为细胞类型的精准注释提供了关键依据，也为后续推断细胞分化轨迹及挖掘微环境互作机制奠定了坚实基础。

### Figure 8: 图 7. 单细胞转录组数据质控指标分布图。

左至右依次展示每个细胞检测到的基因数、总读数及线粒体基因表达占比，Y 轴均表示对应指标的数值。

**Section Summary:** 本研究在单细胞分析流程初期采用小提琴图对 n_genes_by_counts、total_counts 和 pct_counts_mt 三项核心质控指标进行可视化评估，旨在区分高质量细胞与双细胞、空液滴或应激凋亡细胞。图中显示大多数细胞的基因检出数与总读数呈集中分布，而线粒体基因占比普遍低于 5%，仅少数细胞呈现异常高值。基于此分布特征，流程设定了线粒体占比小于 5% 且基因数小于 2500 的过滤阈值，有效剔除了技术噪音与低活性细胞。该质控步骤显著提升了数据集的信噪比，确保后续降维聚类与轨迹推断能够聚焦于真实的生物学异质性，为精准解析细胞亚群发育状态奠定可靠的数据基础。
