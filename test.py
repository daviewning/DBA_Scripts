CREATE OR REPLACE FUNCTION py_spacy(str string) RETURNS STRING 
LANGUAGE PYTHON RUNTIME_VERSION = 3.8 
HANDLER = 'process' 
PACKAGES = ('pandas', 'spacy') 
IMPORTS = ('@my_stage/difficulty_spans_v4_sf_sc.zip', '@my_stage/en_core_web_sm_id_no_sent.zip') AS $$ 
import fcntl 
import logging 
import os 
import pandas as pd 
import spacy 
import sys 
import threading 
import zipfile

from _snowflake import vectorized

logger = logging.getLogger('my_logger')

File lock class for synchronizing write access to /tmp.
class FileLock: def enter(self): self._lock = threading.Lock() self._lock.acquire() self._fd = open('/tmp/lockfile.LOCK', 'w+') fcntl.lockf(self._fd, fcntl.LOCK_EX)

def __exit__(self, type, value, traceback):
    self._fd.close()
    self._lock.release()
Get the location of the import directory. Snowflake sets the import
directory location so code can retrieve the location via sys._xoptions.
IMPORT_DIRECTORY_NAME = "snowflake_import_directory" import_dir = sys._xoptions[IMPORT_DIRECTORY_NAME]

Get the path to the ZIP file and set the location to extract to.
#zip_file_path = import_dir + 'model-best.zip' zip_file_path = import_dir + 'en_core_web_sm_id_no_sent.zip' #extracted = '/tmp/model-best' extracted = '/tmp/en_core_web_sm_id_no_sent'

Extract the contents of the ZIP. This is done under the file lock
to ensure that only one worker process unzips the contents.
with FileLock(): #if not os.path.isdir(extracted + '/model-best'): if not os.path.isdir(extracted + '/en_core_web_sm_id_no_sent'): with zipfile.ZipFile(zip_file_path, 'r') as myzip: myzip.extractall(extracted)

Load the model from the extracted file.
#nlp = spacy.load(extracted + '/model-best') sys.path.insert(1, extracted + '/en_core_web_sm_id_no_sent') import id_matcher nlp = spacy.load(extracted + '/en_core_web_sm_id_no_sent')

@vectorized(input=pd.DataFrame) def process_tmp(df): return pd.Series([','.join(list(set([span.label_ for span in doc.spans['sc']]))) for doc in nlp.pipe(df[0])])

@vectorized(input=pd.DataFrame) def process(df): logger.info('Number of rows:' + str(len(df))) return pd.Series([','.join([str(doc[span.start:span.end]) + ':' + str(span.label_) for span in doc.spans['INTELLECTUAL_DISABILITY']]) for doc in nlp.pipe(df[0])])
$$;
