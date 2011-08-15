'''
performs all the initialization stuff to access JMad from python.

Created on Nov 11, 2010

@author: kaifox
'''

# py4j for communicating with jmad
from py4j.java_gateway import JavaGateway
from pymad.abc import PyMadService

from variables import Enums
from jpymad.modeldef import JPyMadModelDefinition
from jpymad.model import JPyMadModel
from globals import GCont


class JPyMadService(PyMadService):
    """
    the service which is the main facade for the JPyMad - implementation
    """
    
    def __init__(self, new=False):
        super(JPyMadService, self)
        self.jmad_service = None
        
        if (new):
            self._create_new()
        
        self._connect()
        
    def _create_new(self):
        pass

    def is_connected(self):
        """
        returns true, if a connection is established, false if not.
        """
        return not (self.jmad_service == None)
    
    def _connect(self):
        """
        Creates the gateway and the jmad service
        """
        
        # if the java-gateway was already initialized, then we have nothing to do!
        if self.is_connected():
            return
        
        if GCont.java_gateway == None:
            GCont.java_gateway = JavaGateway()
        
        if self.jmad_service == None:
            # the entry-point is directly the jmad service
            # test the connection
            try:
                str = GCont.java_gateway.jvm.java.lang.String #@UndefinedVariable
            except:
                raise
            else:
                # only assign the jmad_service, if no error occured
                self.jmad_service = GCont.java_gateway.entry_point #@UndefinedVariable
        
        # now, that everything is connected, we can init the variables
        GCont.enums = Enums(GCont.java_gateway)
        
    def get_mdefs(self):
        model_definition_manager = self.jmad_service.getModelDefinitionManager()
        mdefs = []
        for model_definition in model_definition_manager.getAllModelDefinitions():
            mdefs.append(JPyMadModelDefinition(model_definition))
        
        return mdefs
    
    def get_models(self):
        model_manager = self.jmad_service.getModelManager()
        return [JPyMadModel(model) for model in model_manager.getModels()]
    
    def get_mdef(self, name):
        ''' returns the model definition of the given name '''
        model_definition_manager = self.jmad_service.getModelDefinitionManager()
        model_definition = model_definition_manager.getModelDefinition(name)
        return JPyMadModelDefinition(model_definition)
    
    def create_model(self, mdef):
        if  isinstance(mdef, str):
            model_definition =  self.get_mdef(mdef)
            if model_definition == None:
                raise Exception("Model definition '" + mdef + "' not found.")
        else:
            model_definition = mdef
    
        jmm = self.jmad_service.createModel(model_definition.jmmd)
        jmm.init()
        return JPyMadModel(jmm)

    def am(self):
        """
        retrieves the active model from the model manager
        """
        model_manager = self.jmad_service.getModelManager()
        active_model = model_manager.getActiveModel()
        if active_model == None:
            return None
        else:
            return JPyMadModel(active_model) 

    def set_am(self, pymadmodel):
        model_manager = self.jmad_service.getModelManager()
        model_manager.setActiveModel(pymadmodel.jmm)



    
    
        

    
   
    

