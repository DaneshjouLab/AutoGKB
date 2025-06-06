""" 
normalization_variants

this file helps normalize entitites extracted via the pipeline. 


see the possible values that it can be noramlizned 

"""


#RSID dbSNP... 


# HGVS genomic https://mutalyzer.nl/hgvs-name-checker

# RefSeqGene (NG) genomic HGVS


#genomic HGVS


#transcript HGVS

# protein HGVS

#RefseqGene HGVSno
# 
# 
# 
"""
HGVS Variant Representations:

NC_000001.11:g.123456A>G (genomic HGVS)

NM_000546.5:c.215C>G (coding DNA / cDNA)

NR_123456.1:n.123G>A (noncoding RNA)

NP_000537.3:p.Arg72Pro (protein-level change)

NG_013339.2:g.4760C>T (RefSeqGene genomic HGVS)

NC_012920.1:m.3243A>G (mitochondrial DNA)

dbSNP Identifiers:

rs123456

123456 (numeric dbSNP ID)

SPDI Format (NCBI):

NC_000001.11:123456:A:G (Sequence Position Deleted Inserted)

VCF-style Representations:

chr1 123456 . A G (VCF line components)

chr1:123456:A>G (compact variant notation)

1-123456-A-G (gnomAD-style key)

Transcript/Exon-specific Formats:

ENST00000335137.3:c.215C>G (Ensembl transcript HGVS)

NM_000546.5:c.215-3A>G (intronic variant)

NM_000546.5:c.*123T>A (3' UTR variant)

NM_000546.5:c.-5G>A (5' UTR variant)

Genotype Representations:

0/0 (homozygous reference)

0/1 (heterozygous unphased)

1/1 (homozygous alternate)

0|1 (phased genotype)

1|2 (multi-allelic phased)

Multi-allelic or Structural:

chr1:123456:A:del (deletion)

chr1:123456:ATG:insT (insertion)

chr1:123456:CTG:GT (multi-nucleotide polymorphism)

Named Haplotypes:

CYP2D6*1

CYP2C19*2

HLA-A*02:01

DPYD*13

HGVS Compound Alleles:

NM_000546.5:c.[215C>G;216T>A] (in cis)

NM_000546.5:c.[215C>G(;)216T>A] (unknown phase)

Phased Haplotype Blocks:

chr1:123456:A>G|chr1:123789:C>T (phased variants)

Protein Consequences (non-HGVS):

p.V600E

Arg72Pro

p.Gly12Asp

COSMIC IDs:

COSM476

ClinVar Variation IDs:

VCV000012345.6

gnomAD/Ensembl Variant Keys:

1-123456-A-G


"""



# for the instance that we are trying to do tyou 