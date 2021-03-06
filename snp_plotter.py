#!usr/bin/env python

import sys
import csv
import sqlite3
import os
import argparse
import dhsquery

def resolve_output_fp(input_fp):
    output_fp = input_fp
    if ('/' in output_fp):
        while not (output_fp.endswith('/')):
            output_fp = output_fp[:len(output_fp)-1]
        output_fp = output_fp[:len(output_fp)-1]
    else:
        output_fp = ''
    return output_fp
                        
def prep_snps(input_fp):
    snp_list = []
    snp_done = []
    if os.path.isfile(input_fp):
        with open (input_fp, 'rb') as infile:
            reader = csv.reader(infile, delimiter = '\t')
            next(reader, None)
            for line in reader:
                snp = line[0]
                if snp not in snp_done:
                    snp_done.append(snp)
                    snp_list.append(line)
    return snp_list

def find_dhs(snp_list, dhsDB):
    conn = sqlite3.connect(dhsDB)
    conn.text_factory = str
    cur = conn.cursor()
    dhs_list = []
    
    for snp_rec in snp_list:
        snp = snp_rec[0]
        snp_chr = 'chr'+snp_rec[1]
        snp_pos = int(snp_rec[2])
        dhs_data = []
        print '\t Checking if '+ snp + ' lies in a DHS'
        cur.execute("SELECT rowid, chr, start, end FROM dhs112 WHERE chr = ? \
                        AND start <= ? AND end >= ?", \
                        (snp_chr, snp_pos, snp_pos))
        query_data = cur.fetchone()
        if query_data is not None:
            dhs_id = query_data[0]
            dhs_start = int(query_data[2])
            dhs_end = int(query_data[3])
            dhs_center = dhs_start + ((dhs_end - dhs_start)/2)
            snp_distance = snp_pos - dhs_center
            dhs_list.append([snp, snp_chr, snp_pos, dhs_id, dhs_start, dhs_end, \
                                 dhs_center, snp_distance])
        else:
            start = snp_pos
            stop = snp_pos
            for i in xrange(0, 400000):
                start -=   250
                stop +=  250
                cur.execute("SELECT rowid, chr, start, end FROM dhs112 \
                                WHERE chr = ? AND start >= ? AND end <= ?; ", \
                                (snp_chr, start, stop))
                q_data = cur.fetchall()
                if q_data is not None:
                    for dhs in q_data:
                        dhs_id = dhs[0]
                        dhs_start = int(dhs[2])
                        dhs_end = int(dhs[3])
                        dhs_center = dhs_start + ((dhs_end - dhs_start)/2)
                        snp_distance = snp_pos - dhs_center
                        dhs_list.append([snp, snp_chr, snp_pos, dhs_id, \
                                             dhs_start, dhs_end, dhs_center, \
                                             snp_distance])
                    break
    
    with open(output_fp + '/snp_dhs_map.txt', 'wb') as out:
        writer = csv.writer(out, delimiter = '\t')
        writer.writerow(['SNP', 'SNP_CHR', 'SNP_POS', 'DHS_ID', 'DHS_START', \
                             'DHS_END', 'DHS_CENTER', 'SNP_DHS_DISTANCE'])
        writer.writerows(dhs_list)


def get_dhs(snp_list, dhsDB):
    conn = sqlite3.connect(dhsDB)
    conn.text_factory = str
    cur = conn.cursor()

    dhs_list = []
    for snp_rec in snp_list:
        snp = snp_rec[0]
        snp_chr = 'chr'+snp_rec[1]
        snp_pos = int(snp_rec[2])
        dhs_data = []
        print '\t Checking if '+ snp + ' lies in a DHS'
        dhs = list(dhsquery.get_snpDHS(snp, snp_chr, snp_pos, dhsDB))
        if dhs[3] != 'NA':
            dhs_start = int(dhs[4])
            dhs_end = int(dhs[5])
            dhs_center = dhs_start + ((dhs_end - dhs_start)/2)
            snp_distance = snp_pos - dhs_center
            dhs.append(snp_distance)
            dhs_list.append(dhs)
            
        else:
            start = snp_pos
            stop = snp_pos
            for i in xrange(0, 400000):
                start -=   250
                stop +=  250
                cur.execute("SELECT rowid, chr, start, end FROM dhs112 \
                                WHERE chr = ? AND start >= ? AND end <= ?; ", \
                                (snp_chr, start, stop))
                q_data = cur.fetchall()
                if q_data is not None:
                    for dhs in q_data:
                        dhs_id = dhs[0]
                        dhs_start = int(dhs[2])
                        dhs_end = int(dhs[3])
                        dhs_center = dhs_start + ((dhs_end - dhs_start)/2)
                        snp_distance = snp_pos - dhs_center
                        cur.execute("SELECT chr, start, end, refined_cluster \
                                       FROM dhsCluster LIMIT 1 OFFSET " \
                                        + str(dhs_id) + ";")
                        data = cur.fetchone()
                        cluster_id = data[3]
                        open_Samples = dhsquery.get_openSamples(cluster_id, dhsDB)
                        overlaps = dhsquery.get_overlaps(cluster_id, dhsDB)
                        motifs = dhsquery.get_motifs(cluster_id, dhsDB)
                        sig_dhsSamples = dhsquery.get_sampleDHS_signal(dhs_id, dhsDB)
                        snp_dhs = (snp, snp_chr, snp_pos, dhs_id, dhs_start, \
                                       dhs_end, sig_dhsSamples[1], cluster_id, \
                                       motifs[1], open_Samples[9], \
                                       open_Samples[10], open_Samples[11], \
                                       snp_distance)
                        dhs_list.append(snp_dhs)
                    break

    
    with open(output_fp + '/snp_dhs.txt', 'wb') as out:
        writer = csv.writer(out, delimiter = '\t')
        writer.writerow(['SNP', 'SNP_CHR', 'SNP_POS', 'DHS_ID', 'DHS_START',\
                             'DHS_END', 'DHS_CELLTYPES', 'CLUSTER_ID', \
                              'TFs', 'MAX_SAMPLE', 'MAX_CELLTYPE', \
                             'MAX_TISSUE', 'SNP_DHS_DISTANCE'])
        writer.writerows(dhs_list)


            


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required = True, \
                            help = 'Significant SNP-eQTL pairs from CoDeS3D')
    parser.add_argument('-d', '--dhsDB', default = '/mnt/3dgenome/projects/' + \
                            'tfad334/dhs/dhs-mining/dhs.db')
    args = parser.parse_args()
    snps = prep_snps(args.input)
    output_fp = resolve_output_fp(args.input)
    get_dhs(snps, args.dhsDB)
    find_dhs(snps, args.dhsDB)

