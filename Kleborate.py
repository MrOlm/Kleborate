# run chromosome, yersiniabactin and colibactin MLST on a Klebs genome
# optionally, run resistance gene screening
import string, re, collections
import os, sys, subprocess
import gzip
from optparse import OptionParser
	
def main():

	usage = "usage: %prog [options]"
	parser = OptionParser(usage=usage)

	# options
	parser.add_option("-p", "--path", action="store", dest="repo_path", help="Path to Kleborate directory (default Kleborate)", default="Kleborate")
	parser.add_option("-o", "--outfile", action="store", dest="outfile", help="File for detailed output (default Kleborate_results.txt)", default="Kleborate_results.txt")
	parser.add_option("-r", "--resistance", action="store", dest="resistance", help="Resistance genes screening (default off, set to on)", default="off")
	
	return parser.parse_args()


def get_compression_type(filename):
	"""
	Attempts to guess the compression (if any) on a file using the first few bytes.
	http://stackoverflow.com/questions/13044562
	"""
	magic_dict = {'gz': (b'\x1f', b'\x8b', b'\x08'),
				  'bz2': (b'\x42', b'\x5a', b'\x68'),
				  'zip': (b'\x50', b'\x4b', b'\x03', b'\x04')}
	max_len = max(len(x) for x in magic_dict)

	unknown_file = open(filename, 'rb')
	file_start = unknown_file.read(max_len)
	unknown_file.close()
	compression_type = 'plain'
	for filetype, magic_bytes in magic_dict.items():
		if file_start.startswith(magic_bytes):
			compression_type = filetype
	if compression_type == 'bz2':
		sys.exit('cannot use bzip2 format - use gzip instead')
	if compression_type == 'zip':
		sys.exit('cannot use zip format - use gzip instead')
	return compression_type


def decompress_file(in_file, out_file):
	with gzip.GzipFile(in_file, 'rb') as i, open(out_file, 'wb') as o:
		s = i.read()
		o.write(s)


if __name__ == "__main__":

	(options, args) = main()

	header_string = "\t".join(["strain","ST","Yersiniabactin","YbST","Colibactin","CbST","aerobactin","salmochelin","hypermucoidy","wzi","KL"])
	print header_string,
	
	res_header_string = ""
	if options.resistance == "on":
		f = os.popen("python "+ options.repo_path + "/resBLAST.py -s " + options.repo_path + "/data/ARGannot.r1.fasta -t " + options.repo_path + "/data/ARGannot_clustered80.csv") 
		fields = f.readline().rstrip().split("\t")
		res_header_string = "\t".join(fields[1:])
		f.close()
		print "\t" + res_header_string,
	
	print "" # end header
		
	mlst_header_string = "\t".join(["Chr_ST","gapA","infB","mdh","pgi","phoE","rpoB","tonB","YbST","ybtS","ybtX","ybtQ","ybtP","ybtA","irp2","irp1","ybtU","ybtT","ybtE","fyuA","CbST","clbA","clbB","clbC","clbD","clbE","clbF","clbG","clbH","clbI","clbL","clbM","clbN","clbO","clbP","clbQ"])
	
	o = file(options.outfile, "w")
	o.write("\t".join([header_string,mlst_header_string]))
	if options.resistance == "on":
		o.write("\t" + res_header_string)
	o.write("\n")

	for contigs in args:
		(dir,fileName) = os.path.split(contigs)
		(name,ext) = os.path.splitext(fileName)
		
		# If the contigs are in a gz file, make a temporary decompressed FASTA file.
		if get_compression_type(contigs) == 'gz':
			new_contigs = contigs + '_temp_decompress.fasta'
			decompress_file(contigs, new_contigs)
			contigs = new_contigs
			temp_decompress = True
		else:
			temp_decompress = False

		f = os.popen("python "+ options.repo_path + "/mlstBLAST.py -s "+ options.repo_path + "/data/Klebsiella_pneumoniae.fasta -d "+ options.repo_path + "/data/kpneumoniae.txt -i no --maxmissing 3 " + contigs) 

		# run chromosome MLST
		chr_ST = ""
		chr_ST_detail = []
		
		for line in f:
			fields = line.rstrip().split("\t")
			if fields[1] != "ST":
				# skip header
				(strain, chr_ST) = (fields[0], fields[1])
				chr_ST_detail = fields[2:]
				if chr_ST != "0":
					chr_ST = "ST"+chr_ST
		f.close()
		
		# run ybt MLST
		
		f = os.popen("python "+ options.repo_path + "/mlstBLAST.py -s "+ options.repo_path + "/data/ybt_alleles.fasta -d "+ options.repo_path + "/data/YbST_profiles.txt -i yes --maxmissing 3 " + contigs) 

		Yb_ST = ""
		Yb_group = ""
		Yb_ST_detail = []
		
		for line in f:
			fields = line.rstrip().split("\t")
			if fields[2] != "ST":
				# skip header
				(strain,Yb_ST, Yb_group) = (fields[0], fields[2], fields[1])
				Yb_ST_detail = fields[3:]
				if Yb_group == "":
					Yb_group = "-"
		f.close()
		
		# run colibactin MLST
		
		f = os.popen("python "+ options.repo_path + "/mlstBLAST.py -s "+ options.repo_path + "/data/colibactin_alleles.fasta -d "+ options.repo_path + "/data/CbST_profiles.txt -i yes --maxmissing 3 " + contigs) 

		Cb_ST = ""
		Cb_group = ""
		Cb_ST_detail = []
		
		for line in f:
			fields = line.rstrip().split("\t")
			if fields[2] != "ST":
				# skip header
				(strain,Cb_ST, Cb_group) = (fields[0],fields[2], fields[1])
				Cb_ST_detail = fields[3:]
				if Cb_group == "":
					Cb_group = "-"
		f.close()
		
		# screen for other virulence genes (binary calls)

		f = os.popen("python "+ options.repo_path + "/clusterBLAST.py -s "+ options.repo_path + "/data/other_vir_clusters.fasta " + contigs) 
		for line in f:
			fields = line.rstrip().split("\t")
			if fields[1] != "aerobactin":
				# skip header
				(strain,vir_hits) = (fields[0],"\t".join(fields[1:]))
		f.close()
		
		# screen for wzi allele
		f = os.popen("python "+ options.repo_path + "/mlstBLAST.py -s " + options.repo_path + "/data/wzi.fasta -d " + options.repo_path + "/data/wzi.txt -i yes --maxmissing 0 -m 99 " + contigs) 
		for line in f:
			fields = line.rstrip().split("\t")
			if fields[0] != "ST":
				# skip header
				(strain, wzi_ST, Ktype) = (fields[0], "wzi" + fields[2], fields[1])
				if fields[2] == "0":
					wzi_ST = "0"
				if Ktype == "":
					Ktype = "-"

		# screen for resistance genes
		res_hits = ""
		if options.resistance == "on":
			f = os.popen("python "+ options.repo_path + "/resBLAST.py -s " + options.repo_path + "/data/ARGannot.r1.fasta -t " + options.repo_path + "/data/ARGannot_clustered80.csv -q" + options.repo_path + "/data/QRDR_120.aa " + contigs) 
			for line in f:
				fields = line.rstrip().split("\t")
				if fields[0] != "strain":
					# skip header
					res_hits = "\t".join(fields[1:])	
			f.close()

		# record results
		print "\t".join([name,chr_ST,Yb_group,Yb_ST,Cb_group,Cb_ST,vir_hits,wzi_ST,Ktype]),
		if options.resistance == "on":
			print "\t" + res_hits,
		print ""
		
		o.write("\t".join([name,chr_ST,Yb_group,Yb_ST,Cb_group,Cb_ST,vir_hits,wzi_ST,Ktype,chr_ST]+chr_ST_detail+[Yb_ST]+Yb_ST_detail + [Cb_ST] + Cb_ST_detail))
		if options.resistance == "on":
			o.write("\t" + res_hits)
		o.write("\n")

		# run Kaptive




		# If we've been working on a temporary decompressed file, delete it now.
		if temp_decompress:
			os.remove(contigs)
		
	o.close()
