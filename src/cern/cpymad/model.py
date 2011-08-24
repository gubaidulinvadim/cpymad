#-------------------------------------------------------------------------------
# This file is part of PyMad.
# 
# Copyright (c) 2011, CERN. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# 	http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#-------------------------------------------------------------------------------
'''
.. module: cpymad.model

Cython implementation of the model api.
:See also: :mod:`pymad.abc.model`

.. moduleauthor:: Yngve Inntjore Levinsen <Yngve.Inntjore.Levinsen@cern.ch>

'''

import json, os, sys
from cern.madx import madx
import cern.cpymad
#from cern.pymad import abc.model
import multiprocessing
import signal,atexit
from cern.pymad.globals import USE_COUCH

#class model(model.PyMadModel):
class model():
    '''
    model class implementation. the model spawns a madx instance in a separate process.
    this has the advantage that you can run separate models which do not affect each other.
     
    :param string model: Name of model to load.
    :param string optics: Name of optics to load
    :param string histfile: Name of file which will contain all Mad-X commands called.
    '''
    def __init__(self,model,optics='',histfile=''):
        
        # name of model:
        self.model=model
        # loading the dictionary...
        self._dict=_get_data(model)
        
        # Defining two pipes which are used for communicating...
        _child_pipe_recv,_parent_send=multiprocessing.Pipe(False)
        _parent_recv,_child_pipe_send=multiprocessing.Pipe(False)
        self._send=_parent_send.send
        self._recv=_parent_recv.recv
        if not USE_COUCH:
            for d in self._dict['dbdirs']:
                if os.path.isdir(d):
                    self._db=d
                    break
        
        self._mprocess=_modelProcess(_child_pipe_send,_child_pipe_recv,model,histfile)
        
        self._mprocess.start()
        
        atexit.register(self._mprocess.terminate)
        
        self._call(self._dict['sequence'])
        
        self._optics=''
        
        self.set_optics(optics)
        
        # To keep track of whether or not certain things are already called..
        self._apercalled={}
        self._twisscalled={}
        for seq in self.get_sequences():
            self._apercalled[seq]=False
            self._twisscalled[seq]=False
        
    
    def __del__(self):
        try:
            self._send('delete_model')
            self._mprocess.join(5)
        except TypeError: pass
    
    def __str__(self):
        return self.model
    
    def _call(self,f):
        if USE_COUCH:
            cmd=cern.cpymad._couch_server.get_file(self.model,f)
            for c in cmd.split('\n'): # I wonder if this might be needed for now?
                ret=self._sendrecv(('command',cmd))
            return ret
        return self._sendrecv(('call',self._db+f))
    
    def has_sequence(self,sequence):
        '''
         Check if model has the sequence.
         
         :param string sequence: Sequence name to be checked.
        '''
        return sequence in self.get_sequences()
    
    def has_optics(self,optics):
        '''
         Check if model has the optics.
         
         :param string optics: Optics name to be checked.
        '''
        return optics in self._dict['optics']
    
    def set_optics(self,optics):
        '''
         Set new optics.
         
         :param string optics: Optics name.
         
         :raises KeyError: In case you try to set an optics not available in model.
        '''
        if optics=='':
            optics=self._dict['default']['optics']
        if self._optics==optics:
            print("INFO: Optics already initialized")
            return 0
        
        # optics dictionary..
        odict=self._dict['optics'][optics]
        # knobs dictionary..
        bdict=self._dict['beams']
        
        for strfile in odict['strengths']:
            self._call(strfile)
        
        for f in odict['knobs']:
            if odict['knobs'][f]:
                self.set_knob(f,1.0)
            else:
                self.set_knob(f,0.0)
        
        for b in odict['beams']:
            self._cmd(bdict[b])
        self._optics=optics
    
    def set_knob(self,knob,value):
        kdict=self._dict['knobs']
        for e in kdict[knob]:
            val=str(kdict[knob][e]*value)
            self._cmd(e+"="+val)
    
    def get_sequences(self):
        return self._sendrecv('get_sequences')
    
    def list_optics(self):
        return self._dict['optics'].keys()
    
    def twiss(self,
              sequence='',
              columns='name,s,betx,bety,x,y,dx,dy,px,py,mux,muy',
              twrange='',
              fname='',
              retdict=False):
        '''
         Run a TWISS on the model.
         
         :param string sequence: Sequence, if empty, using default sequence.
         :param string columns: Columns in the twiss table, can also be list of strings
         :param string twrange: Optional, give name of a range defined for the model.
         :param string fname: Optionally, give name of file for tfs table.
         :param bool retdict: Return dictionaries (default is an extended LookUpDict)
        '''
        from cern.pymad.domain import TfsTable, TfsSummary
        if sequence=='':
            sequence=self._dict['default']['sequence']
        t,s=self._sendrecv(('twiss',sequence,columns,fname))
        # we say that when the "full" range has been selected, 
        # we can set this to true. Needed for e.g. aperture calls
        if not twrange:
            self._twisscalled[sequence]=True
        if retdict:
            return t,s
        return TfsTable(t),TfsSummary(s)
    
    def survey(self,
               sequence='',
               columns='name,l,angle,x,y,z,theta',
               fname='',
               retdict=False):
        '''
         Run a survey on the model.
         
         :param string sequence: Sequence, if empty, using default sequence.
         :param string columns: Columns in the twiss table, can also be list of strings
         :param string fname: Optionally, give name of file for tfs table.
         :param bool retdict: Return dictionaries (default is an extended LookUpDict)
        '''
        from cern.pymad.domain import TfsTable, TfsSummary
        if sequence=='':
            sequence=self._dict['default']['sequence']
        t,s=self._sendrecv(('survey',sequence,columns,fname))
        if retdict:
            return t,s
        return TfsTable(t),TfsSummary(s)
    
    def aperture(self,
               sequence='',
               arange='',
               columns='name,l,s,n1,aper_1,aper_2,aper_3,aper_4',
               fname='',
               retdict=False):
        '''
         Get the aperture from the model.
         
         :param string sequence: Sequence, if empty, using default sequence.
         :param string arange: Range, if empty, the full sequence is chosen.
         :param string columns: Columns in the twiss table, can also be list of strings
         :param string fname: Optionally, give name of file for tfs table.
         :param bool retdict: Return dictionaries (default is an extended LookUpDict)
        '''
        from cern.pymad.domain import TfsTable, TfsSummary
        if sequence=='':
            sequence=self._dict['default']['sequence']
        seq=self._dict['sequences'][sequence]
        
        if not self._twisscalled[sequence]:
            self.twiss(sequence)
        # Calling "basic aperture files"
        if not self._apercalled[sequence]:
            print seq.keys()
            for afile in seq['aperfiles']:
                self._call(afile)
            self._apercalled[sequence]=True
        # getting offset file if any:
        if arange not in seq['ranges']:
            raise ValueError("%s is not a valid range name, available ranges: '%s'" % (arange,"' '".join(seq['ranges'].keys())))
        onum=seq['ranges'][arange]['offsets']
        ran=seq['ranges'][arange]['range']
        ofile=''
        if onum or onum!=0:
            if USE_COUCH:
                ofile='tmp_madx_offsets.tfs'
                ftmp=file(ofile,'w')
                ftmp.write(cern.cpymad._couch_server.get_file(self.model,seq['offsets'][onum]))
                ftmp.close()
            else:
                ofile=self._db+seq['offsets'][onum]
        
        t,s=self._sendrecv(('aperture',sequence,ran,columns,ofile,fname))
        if retdict:
            return t,s
        return TfsTable(t),TfsSummary(s)
        
    
    def _cmd(self,command):
        self._send(('command',command))
        return self._recv()
    def _sendrecv(self,func):
        if sys.flags.debug:
            print("Sending function call "+str(func))
        self._send(func)
        return self._recv()
        
           
def _get_data(modelname):
    if USE_COUCH:
        return cern.cpymad._couch_server.get_model(modelname)
    fname=modelname+'.json'
    _dict = _get_file_content(modelname,fname)
    return json.loads(_dict)

def _get_file_content(modelname,filename):
    if USE_COUCH:
        return cern.cpymad._couch_server.get_file(modelname,filename)
    filename=os.path.join('_models',filename)
    try:
         import pkgutil
         stream = pkgutil.get_data(__name__, filename)
    except ImportError:
        import pkg_resources
        stream = pkg_resources.resource_string(__name__, filename)
    return stream
    
class _modelProcess(multiprocessing.Process):
    def __init__(self,sender,receiver,model,history=''):
        self.sender=sender
        self.receiver=receiver
        self.model=model
        self.history=history
        multiprocessing.Process.__init__(self) 
    
    def run(self):
        _madx=madx(histfile=self.history)
        _madx.verbose(False)
        _madx.append_model(self.model)
        if USE_COUCH:
            _couch_server=cern.cpymad._couch.couch.Server()
            _madx.command(_couch_server.get_file(self.model,'initscript'))

        def terminator(num, frame):
             sys.exit()
        signal.signal(signal.SIGTERM, terminator)

        while True:
            if self.receiver.poll(2):
                cmd=self.receiver.recv()
                if cmd=='delete_model':
                    self.sender.close()
                    self.receiver.close()
                    break
                elif cmd[0]=='call':
                    _madx.call(cmd[1])
                    self.sender.send('done')
                elif cmd=='get_sequences':
                    self.sender.send( _madx.get_sequences())
                elif cmd[0]=='command':
                    _madx.command(cmd[1])
                    self.sender.send('done')
                elif cmd[0]=='twiss':
                    t,s=_madx.twiss(sequence=cmd[1],columns=cmd[2],fname=cmd[3],retdict=True)
                    self.sender.send((t,s))
                elif cmd[0]=='survey':
                    t,s=_madx.survey(sequence=cmd[1],columns=cmd[2],fname=cmd[3],retdict=True)
                    self.sender.send((t,s))
                elif cmd[0]=='aperture':
                    t,s=_madx.aperture(sequence=cmd[1],madrange=cmd[2],columns=cmd[3],offsets=cmd[4],fname=cmd[5],retdict=True)
                    self.sender.send((t,s))
                else:
                    raise ValueError("You sent a wrong command to subprocess: "+str(cmd))
