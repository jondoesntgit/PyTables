#!/usr/bin/env python

import copy

import time
import numarray as NA
from tables import *
import random

class Small(IsDescription):
    var1 = StringCol(length=4, dflt="")
    var2 = IntCol(0)
    var3 = FloatCol(0)

# Define a user record to characterize some kind of particles
class Medium(IsDescription):
    var1        = StringCol(length=16, dflt="")  # 16-character String
    #float1      = Col("Float64", 1, 2.3)
    #float2      = Col("Float64", 1, 2.3)
    #zADCcount    = Col("Int16", 1, 0)    # signed short integer
    var2        = Col("Int32", 1, 0)    # signed short integer
    var3        = Col("Float64", 1, 0)
    grid_i      = Col("Int32", 1, 0)    # integer
    grid_j      = Col("Int32", 1, 0)    # integer
    pressure    = Col("Float32", 1, 0)    # float  (single-precision)
    energy      = Col("Float64", 2, 0)    # double (double-precision)

def createFile(filename, nrows, filters, atom, recsize, index, verbose):

    # Open a file in "w"rite mode
    fileh = openFile(filename, mode = "w", title="Searchsorted Benchmark",
                     filters=filters)
    title = "This is the IndexArray title"
    # Create an IndexArray instance
    rowswritten = 0
    # Create an entry
    klass = {"small":Small, "medium":Medium}
    table = fileh.createTable(fileh.root, 'table', klass[recsize], title,
                              None, nrows)
    for i in range(nrows):
        # table.row['var1'] = str(i)
        #table.row['var2'] = random.randrange(nrows)
        table.row['var2'] = i
        table.row['var3'] = i
        table.row.append()
    rowswritten += nrows
    table.flush()
    rowsize = table.rowsize
    indexrows = 0
        
    # Index one entry:
    if index:
        if atom == "int":
            indexrows = table.cols.var2.createIndex()
        elif atom == "float":
            indexrows = table.cols.var3.createIndex()
        else:
            raise ValueError, "Index type not supported yet"
        if verbose:
            print "Number of indexed rows:", indexrows
    # Close the file (eventually destroy the extended type)
    fileh.close()
    
    return (rowswritten, rowsize)

def readFile(filename, atom, niter, verbose):
    # Open the HDF5 file in read-only mode

    fileh = openFile(filename, mode = "r")
    table = fileh.root.table
    print "reading", table
    if verbose:
        print "Max rows in buf:", table._v_maxTuples
        print "Rows in", table._v_pathname, ":", table.nrows
        print "Buffersize:", table.rowsize * table._v_maxTuples
        print "MaxTuples:", table._v_maxTuples

    for i in xrange(niter):
        if atom == "int":
            #results = [table.row["var3"] for i in table(where=2+i<=table.cols.var2 < 10+i)]
#             results = [table.row.nrow() for i in table(where=2<=table.cols.var2 < 10)]
            results = [p.nrow()
                       for p in table(where=6-i<=table.cols.var2<6+i)]
        elif atom == "float":
#         results = [(table.row.nrow(), table.row["var3"])
#                    for i in table(where=3<=table.cols.var3 < 5.)]
#             results = [(p.nrow(), p["var3"])
#                        for p in table(where=1000.-i<=table.cols.var3<1000.+i)]
            results = [(p.nrow(), p["var3"]) 
                       for p in table(where=table.cols.var3>=100000-i)]
#             results = [ (p.nrow(), p["var3"]) for p in table
#                         if (1000.-i <= p["var3"] < 1000.+i) ]
        else:
            raise ValueError, "Unsuported atom value"
    if verbose and 1:
        print "Values that fullfill the conditions:"
        print results

    rowsread = table.nrows * niter
    rowsize = table.rowsize 
    rowselected = len(results) * niter
        
    # Close the file (eventually destroy the extended type)
    fileh.close()

    return (rowsread, rowselected, rowsize)


def searchFile(filename, atom, verbose, item):
    # Open the HDF5 file in read-only mode

    fileh = openFile(filename, mode = "r")
    rowsread = 0
    uncomprBytes = 0
    table = fileh.root.table
    rowsize = table.rowsize
    if atom == "int":
        idxcol = table.cols.var2.index
    elif atom == "float":
        idxcol = table.cols.var3.index
    else:
        raise ValueError, "Unsuported atom value"
    print "Searching", table, "..."
    if verbose:
        print "Chunk size:", idxcol.sorted.chunksize
        print "Number of elements per slice:", idxcol.sorted.nelemslice
        print "Slice number in", table._v_pathname, ":", idxcol.sorted.nrows

    (positions, niter) = idxcol.search(item)
    if verbose:
        print "Positions for item",item,"==>",positions
        print "Total iterations in search:", niter

    rowsread += table.nrows
    uncomprBytes += idxcol.sorted.chunksize * niter * idxcol.sorted.itemsize

    results = table.read(coords=positions)
    print "results length:", len(results)
    if verbose:
        print "Values that fullfill the conditions:"
        print results
        
    # Close the file (eventually destroy the extended type)
    fileh.close()

    return (rowsread, uncomprBytes, niter)


if __name__=="__main__":
    import sys
    import getopt
    try:
        import psyco
        psyco_imported = 1
    except:
        psyco_imported = 0
    
    import time
    
    usage = """usage: %s [-v] [-p] [-R range] [-r] [-w] [-s recsize ] [-a
    atom] [-c level] [-l complib] [-S] [-F] [-i item] [-n nrows] [-x]
    [-k niter] file
            -v verbose
	    -p use "psyco" if available
            -R select a range in a field in the form "start,stop,step"
	    -r only read test
	    -w only write test
            -s record size
            -a use [float], [int], [bool] or [string] atom
            -c sets a compression level (do not set it or 0 for no compression)
            -S activate shuffling filter
            -F activate fletcher32 filter
            -l sets the compression library to be used ("zlib", "lzo", "ucl")
            -i item to search
            -n set the number of rows in tables
            -x don't make indexes
            -k number of iterations for reading\n""" % sys.argv[0]

    try:
        opts, pargs = getopt.getopt(sys.argv[1:], 'vpSFR:rwxk:s:a:c:l:i:n:')
    except:
        sys.stderr.write(usage)
        sys.exit(0)

    # if we pass too much parameters, abort
    if len(pargs) <> 1: 
        sys.stderr.write(usage)
        sys.exit(0)

    # default options
    verbose = 0
    rng = None
    item = None
    atom = "int"
    fieldName = None
    testread = 1
    testwrite = 1
    usepsyco = 0
    complevel = 0
    shuffle = 0
    fletcher32 = 0
    complib = "zlib"
    nrows = 100
    recsize = "small"
    index = 1
    niter = 1

    # Get the options
    for option in opts:
        if option[0] == '-v':
            verbose = 1
        if option[0] == '-p':
            usepsyco = 1
        if option[0] == '-S':
            shuffle = 1
        if option[0] == '-F':
            fletcher32 = 1
        elif option[0] == '-R':
            rng = [int(i) for i in option[1].split(",")]
        elif option[0] == '-r':
            testwrite = 0
        elif option[0] == '-w':
            testread = 0
        elif option[0] == '-x':
            index = 0
        elif option[0] == '-s':
            recsize = option[1]
        elif option[0] == '-a':
            atom = option[1]
            if atom not in ["float", "int", "bool", "string"]:
                sys.stderr.write(usage)
                sys.exit(0)
        elif option[0] == '-c':
            complevel = int(option[1])
        elif option[0] == '-l':
            complib = option[1]
        elif option[0] == '-i':
            item = eval(option[1])
        elif option[0] == '-n':
            nrows = int(option[1])
        elif option[0] == '-k':
            niter = int(option[1])
            
    # Build the Filters instance
    filters = Filters(complevel=complevel, complib=complib,
                      shuffle=shuffle, fletcher32=fletcher32)

    # Catch the hdf5 file passed as the last argument
    file = pargs[0]

    if testwrite:
        print "Compression level:", complevel
        if complevel > 0:
            print "Compression library:", complib
            if shuffle:
                print "Suffling..."
	t1 = time.time()
	cpu1 = time.clock()
        if psyco_imported and usepsyco:
            psyco.bind(createFile)
	(rowsw, rowsz) = createFile(file, nrows, filters,
                                    atom, recsize, index, verbose)
	t2 = time.time()
        cpu2 = time.clock()
	tapprows = round(t2-t1, 3)
	cpuapprows = round(cpu2-cpu1, 3)
        tpercent = int(round(cpuapprows/tapprows, 2)*100)
	print "Rows written:", rowsw, " Row size:", rowsz
	print "Time writing rows: %s s (real) %s s (cpu)  %s%%" % \
              (tapprows, cpuapprows, tpercent)
	print "Write rows/sec: ", int(rowsw / float(tapprows))
	print "Write KB/s :", int(rowsw * rowsz / (tapprows * 1024))
	
    if testread:
        if psyco_imported and usepsyco:
            psyco.bind(readFile)
            psyco.bind(searchFile)
	t1 = time.time()
        cpu1 = time.clock()
        if rng or item:
            (rowsr, uncomprB, niter) = searchFile(file, atom, verbose, item)
        else:
            for i in range(1):
                (rowsr, rowsel, rowsz) = readFile(file, atom, niter, verbose)
	t2 = time.time()
        cpu2 = time.clock()
	treadrows = round(t2-t1, 3)
        cpureadrows = round(cpu2-cpu1, 3)
        tpercent = int(round(cpureadrows/treadrows, 2)*100)
        tMrows = rowsr/(1000*1000.)
        sKrows = rowsel/1000.
	print "Rows read:", rowsr, "Mread:", round(tMrows, 3), "Mrows"
	print "Rows selected:", rowsel, "Ksel:", round(sKrows,3), "Krows"
	print "Time reading rows: %s s (real) %s s (cpu)  %s%%" % \
              (treadrows, cpureadrows, tpercent)
	print "Read Mrows/sec: ", round(tMrows / float(treadrows), 3)
	#print "Read KB/s :", int(rowsr * rowsz / (treadrows * 1024))
# 	print "Uncompr MB :", int(uncomprB / (1024 * 1024))
# 	print "Uncompr MB/s :", int(uncomprB / (treadrows * 1024 * 1024))
#	print "Total chunks uncompr :", int(niter)
    
