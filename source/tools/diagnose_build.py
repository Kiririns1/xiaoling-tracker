import runpy,faulthandler,sys,os
faulthandler.enable();faulthandler.dump_traceback_later(40,repeat=True)
os.environ['PYTHONUNBUFFERED']='1'
sys.argv=[os.environ['IDF_PATH']+'/tools/idf.py','-C',os.environ['ADF_PATH']+'/apps','build']
sys.path.insert(0,os.environ['IDF_PATH']+'/tools')
runpy.run_path(sys.argv[0],run_name='__main__')
