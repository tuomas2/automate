# imports from your own library that you are using to define your sensor & actuator
from mylibrary import (setup_data_changed_callback,
                       fetch_data_from_my_datasource,
                       initialize_my_actuator_device,
                       change_status_in_my_actuator_device)

class MySensor(AbstractSensor):
   """
   Let us assume that you have your own library which has a status that you
   want to track in your Automate program.
   """
   # define your status data type
   _status = CBool
   def setup(self):
       setup_my_datasource()
       # we tell our library that update_status need to be called when status is
       # changed. We could use self.set_status directly, if library can pass
       # new status as an argument.
       setup_data_changed_callback(self.update_status)
   def update_status(self):
       # fetch new status from your datasource (this function is called by
       # your library)
       self.status = fetch_data_from_your_datasource()
   def cleanup(self):
       # define this if you need to clean things up when program is stopped
       pass

class MyActuator(AbstractActuator):
   # define your status data type. Transient=True is a good idea because
   # actuator status is normally determined by other values (sensors & programs etc)
   _status = CFloat(transient=True)
   def setup(self):
       initialize_my_actuator_device()
   def _status_changed(self):
       chagnge_status_in_my_actuator_device(self.status)
