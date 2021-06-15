from opcua import Client
from colorama import init, Fore, Back, Style
import helpers.client_helper_funcs as madlad
import numpy as np
import time
from switch import Switch
from ied import IED
import constant


class ServerClient:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.server = None
        self.variables = {}

    def connect(self):
        '''
        Connects to server $server_ip.
        '''
        try:
            server = Client(self.server_ip)
            server.connect()
            print(Fore.CYAN + 'Connected to ' + self.server_ip)
            print('Server Connected')
            self.server = server
        except:
            print(Fore.RED + 'Connection to ' + self.server_ip + 'failed')

    def disconnect(self):
        '''
        Disconnects from server.
        '''
        try:
            self.server.close_session()
            print(Fore.CYAN + 'Succesfully disconnected from ' + self.server_ip)
        except:
            print(Fore.RED + 'Failed to disconnect from ' + self.server_ip)

    def check_all_variable_consistency(self):
        '''
        Check consistency of all variable against themselves.
        For IED will check if corresponding switch is OFF(OPEN).
        '''
        for key, val in self.variables.items():
            if type(val) is Switch:
                val.check_consistency()

                if val.name == 'q1-3' and val.is_open == 1 and val.is_close == 0:
                    self.variables['tied1'].check_off_consistency()
                if val.name == 'q2-1' and val.is_open == 1 and val.is_close == 0:
                    self.variables['tied4'].check_off_consistency()
                if val.name == 'q3' and val.is_open == 1 and val.is_close == 0:
                    self.variables['tied2'].check_off_consistency()

                if val.name == 'q1' and val.is_open == 1 and val.is_close == 0:
                    self.variables['gied1'].check_off_consistency()
                if val.name == 'q1-a' and val.is_open == 1 and val.is_close == 0:
                    self.variables['gied2'].check_off_consistency()

                if val.name == 'q2b' and val.is_open == 1 and val.is_close == 0:
                    self.variables['mied1'].check_off_consistency()
                if val.name == 'q2c' and val.is_open == 1 and val.is_close == 0:
                    self.variables['mied2'].check_off_consistency()

                if val.name == 'q3-1' and val.is_open == 1 and val.is_close == 0:
                    self.variables['sied4'].check_off_consistency()
                if val.name == 'q3-2' and val.is_open == 1 and val.is_close == 0:
                    self.variables['sied3'].check_off_consistency()
                if val.name == 'q3-3' and val.is_open == 1 and val.is_close == 0:
                    self.variables['sied2'].check_off_consistency()
                if val.name == 'q3-4' and val.is_open == 1 and val.is_close == 0:
                    self.variables['sied1'].check_off_consistency()

    def check_case_smart_home(self):
        '''
        The summation of TIED2 and TIED4 should be equal to the summation of SIED1 to 4
        absolute((TIED2 + TIED4) - (SIED1 + SIED2 + SIED3 + SIED4)) <= CURRENT MARGIN
        '''
        tied_sum = 0
        sied_sum = 0

        # TIED2
        if self.variables['q3'].is_open == 0 and self.variables['q3'].is_close == 1:
            tied_sum += self.variables['tied2'].current

        # TIED4
        if self.variables['q2-1'].is_open == 0 and self.variables['q2-1'].is_close == 1:
            tied_sum += self.variables['tied4'].current

        # SIED 1,2,3,4
        i = 3
        for x in range(1, 5):
            if self.variables['q3-' + str(x + i)].is_open == 0 and self.variables['q3-4'].is_close == 1:
                sied_sum += self.variables['sied' + str(x)].current

            i = i - 2

        if np.less(abs(tied_sum - sied_sum), constant.CURRENT_MARGIN).all():
            print(Fore.GREEN + 'Case Smart Home is consistent')
            print()
            return True
        else:
            print(Fore.RED + ' Case Smart Home is NOT consistent')
            print()
            return False

    def check_case_micro_grid(self):
        '''
        The summation of TIED4 should be equal to the summation of MIED1, MIED2,
        25A(Q2) and 63A(Q2A) depending on switch status.
        absolute( TIED4 - (MIED1 + MIED2 + 25A(Q2) + 63A(Q2A))) <= CURRENT MARGIN
        '''
        tied_sum = 0
        mied_sum = 0

        # TIED4
        if self.variables['q2-1'].is_open == 0 and self.variables['q2-1'].is_close == 1:
            tied_sum += self.variables['tied4'].current

        # 25A(Q2)
        if self.variables['q2'].is_open == 0 and self.variables['q2'].is_close == 1:
            mied_sum += 25

        # 63A(Q2A)
        if self.variables['q2a'].is_open == 0 and self.variables['q2a'].is_close == 1:
            mied_sum += 63

        # MIED1
        if self.variables['q2b'].is_open == 0 and self.variables['q2b'].is_close == 1:
            mied_sum += self.variables['mied1'].current

        # MIED2
        if self.variables['q2c'].is_open == 0 and self.variables['q2c'].is_close == 1:
            mied_sum += self.variables['mied2'].current

        if np.less(abs(tied_sum - mied_sum), constant.CURRENT_MARGIN).all():
            print(Fore.GREEN + 'Case Micro Grid is consistent')
            print()
            return True
        else:
            print(Fore.RED + 'Case Micro Grid is NOT consistent')
            print('tied_sum Value ' + str(tied_sum))
            print('mied_sum Value ' + str(mied_sum))
            print()
            return False

    def check_case_generation(self):
        '''
        The summation of GIED2, GIED1 divided by amount of pathways (1 to 4) 
        should be equal to TIED1.
        absolute(((GIED1 + GIED2) / outlet_switch_close_count) - tied_sum) <= CURRENT MARGIN
        outlet_switch_close_count - amount of switches that is close.
        '''
        tied_sum = 0
        gied_sum = 0
        outlet_switch_close_count = 0

        # TIED1
        if self.variables['q1-3'].is_open == 0 and self.variables['q1-3'].is_close == 1:
            outlet_switch_close_count += 1
            tied_sum += self.variables['tied1'].current

        # GIED1
        if self.variables['q1'].is_open == 0 and self.variables['q1'].is_close == 1:
            gied_sum += self.variables['gied1'].current

        # GIED2
        if self.variables['q1a'].is_open == 0 and self.variables['q1a'].is_close == 1:
            gied_sum += self.variables['gied2'].current

        # Q1-1
        if self.variables['q1-1'].is_open == 0 and self.variables['q1-1'].is_close == 1:
            outlet_switch_close_count += 1

        # Q1-2
        if self.variables['q1-2'].is_open == 0 and self.variables['q1-2'].is_close == 1:
            outlet_switch_close_count += 1

        # Q1-4
        if self.variables['q1-4'].is_open == 0 and self.variables['q1-4'].is_close == 1:
            outlet_switch_close_count += 1

        if outlet_switch_close_count == 0:
            result = abs((gied_sum/outlet_switch_close_count))
        else:
            result = 0

        if np.less((result- tied_sum), constant.CURRENT_MARGIN).all():
            print(Fore.GREEN + 'Case Generation is consistent')
            print()
            self.check_case_extended_generation(
                gied_sum, outlet_switch_close_count)
            return True
        else:
            print(Fore.RED + 'Case Generation is NOT consistent')
            print()
            self.check_case_extended_generation(
                gied_sum, outlet_switch_close_count)
            return False

    def check_case_extended_generation(self, generation_sum, outlet_switch_close_count):
        '''
        Case Extended Generation: Need value outlet_switch_close_count and gied_sum from Case Generation.

        If Q2C and Q1-2 is ON(CLOSE), gied_sum divided by amount of
        outlet_switch_close_count should be equal to MIED2.

        If Q2B and Q1-1 is ON(CLOSE), gied_sum divided by amount of
        outlet_switch_close_count should be equal to MIED1.
        '''
        generationValue = generation_sum / outlet_switch_close_count

        # Q2C and Q1-2.
        if (self.variables['q2c'].is_open == 0 and self.variables['q2c'].is_close == 1 and
                self.variables['q1-2'].is_open == 0 and self.variables['q1-2'].is_close == 1):
            if np.less(abs(self.variables['mied2'].current - generationValue),
                       constant.CURRENT_MARGIN).all():
                print(Fore.GREEN + 'Case Extended Generation MIED2 is consistent')
                print()
            else:
                print(Fore.RED + 'Case Extended Generation MIED2 is NOT consistent')
                print()
        else:
            print(
                Fore.GREEN + 'Case Extended Generation MIED2 not called, switches not ON(CLOSE)')
            print()

        # Q2B and Q1-1.
        if (self.variables['q2b'].is_open == 0 and self.variables['q2b'].is_close == 1 and
                self.variables['q1-1'].is_open == 0 and self.variables['q1-1'].is_close == 1):
            if np.less(abs(self.variables['mied1'].current - generationValue),
                       constant.CURRENT_MARGIN).all():
                print(Fore.GREEN + 'Case Extended Generation MIED1 is consistent')
                print()
            else:
                print(Fore.RED + 'Case Extended Generation MIED1 is NOT consistent')
                print()
        else:
            print(
                Fore.GREEN + 'Case Extended Generation MIED1 not called, switches not ON(CLOSE)')
            print()

    def check_case_tied1_tied2(self):
        '''
        TIED1 should be equal to TIED2 If both switches, Q1-3 and Q3 are ON(CLOSE).
        '''
        # Q2C and Q1-2.
        if (self.variables['q1-3'].is_open == 0 and self.variables['q1-3'].is_close == 1 and
                self.variables['q3'].is_open == 0 and self.variables['q3'].is_close == 1):
            if np.less(abs(self.variables['tied1'].current - self.variables['tied2'].current),
                       constant.CURRENT_MARGIN).all():
                print(Fore.GREEN + 'Case TIED1 TIED2 is consistent')
                print()
            else:
                print(Fore.RED + 'Case TIED1 TIED2 is NOT consistent')
                print()
        else:
            print(
                Fore.GREEN + 'Case TIED1 TIED2 not called, switches not ON(CLOSE)')
            print()

    def check_case_sied1_gied2(self):
        '''
        SIED1 should be equal to GIED2 If both switches, Q3-4, Q1A are ON(CLOSE).
        '''
        # Q2C and Q1-2.
        if (self.variables['q3-4'].is_open == 0 and self.variables['q3-4'].is_close == 1 and
                self.variables['q1a'].is_open == 0 and self.variables['q1a'].is_close == 1):
            if np.less(abs(self.variables['sied1'].current - self.variables['gied2'].current),
                       constant.CURRENT_MARGIN).all():
                print(Fore.GREEN + 'Case SIED1 GIED2 is consistent')
                print()
            else:
                print(Fore.RED + 'Case SIED1 GIED2 is NOT consistent')
                print()
        else:
            print(
                Fore.GREEN + 'Case SIED1 GIED2 not called, switches not ON(CLOSE)')
            print()

    def update_client_object(self):
        '''
        Get all items in server/client.
        '''
        madlad.update_EPIC_Objects(self.server)
        time.sleep(2)
        variables = self.get_data()

    def get_data(self):
        '''
        Update variables with all the switches and ieds.
        '''
        # DB - 1 (GENERATION)
        Switch.define_switch('Generation.Q1', madlad.dict, 'q1',
                             self.variables, self.server)

        IED.define_ied('Generation.GIED1.Measurement', madlad.dict, 'gied1',
                       self.variables, self.server)

        Switch.define_switch('Generation.Q1A', madlad.dict, 'q1a',
                             self.variables, self.server)

        IED.define_ied('Generation.GIED2.Measurement', madlad.dict, 'gied2',
                       self.variables, self.server)

        Switch.define_switch('Generation.Q1_1', madlad.dict, 'q1-1',
                             self.variables, self.server)

        Switch.define_switch('Generation.Q1_2', madlad.dict, 'q1-2',
                             self.variables, self.server)

        Switch.define_switch('Generation.Q1_4', madlad.dict, 'q1-4',
                             self.variables, self.server)

        Switch.define_switch('Generation.Q1_5', madlad.dict, 'q1-5',
                             self.variables, self.server)

        Switch.define_switch('Transmission.Q1_3', madlad.dict, 'q1-3',
                             self.variables, self.server)

        IED.define_ied('Transmission.TIED1.Measurement', madlad.dict, 'tied1',
                       self.variables, self.server)

        # # DB - 2 (MICRO GRID)
        Switch.define_switch('MicroGrid.Q2B', madlad.dict, 'q2b',
                             self.variables, self.server)
        IED.define_ied('MicroGrid.MIED1.Measurement', madlad.dict, 'mied1',
                       self.variables, self.server)

        Switch.define_switch('MicroGrid.Q2C', madlad.dict, 'q2c',
                             self.variables, self.server)
        IED.define_ied('MicroGrid.MIED2.Measurement', madlad.dict, 'mied2',
                       self.variables, self.server)

        Switch.define_switch('MicroGrid.Q2', madlad.dict, 'q2',
                             self.variables, self.server)

        Switch.define_switch('MicroGrid.Q2A', madlad.dict, 'q2a',
                             self.variables, self.server)

        Switch.define_switch('Transmission.Q2_1', madlad.dict, 'q2-1',
                             self.variables, self.server)
        IED.define_ied('Transmission.TIED4.Measurement', madlad.dict, 'tied4',
                       self.variables, self.server)

        # # DB - 3 (SMART HOME)
        Switch.define_switch('SmartHome.Q3_4', madlad.dict, 'q3-4',
                             self.variables, self.server)

        IED.define_ied('SmartHome.SIED1.Measurement', madlad.dict,
                       'sied1', self.variables, self.server)

        Switch.define_switch('SmartHome.Q3_3', madlad.dict, 'q3-3',
                             self.variables, self.server)

        IED.define_ied('SmartHome.SIED2.Measurement', madlad.dict, 'sied2',
                       self.variables, self.server)

        Switch.define_switch('SmartHome.Q3_2', madlad.dict, 'q3-2',
                             self.variables, self.server)

        IED.define_ied('SmartHome.SIED3.Measurement', madlad.dict, 'sied3',
                       self.variables, self.server)

        Switch.define_switch('SmartHome.Q3_1', madlad.dict, 'q3-1',
                             self.variables, self.server)

        IED.define_ied('SmartHome.SIED4.Measurement', madlad.dict, 'sied4',
                       self.variables, self.server)

        Switch.define_switch('Transmission.Q3', madlad.dict, 'q3',
                             self.variables, self.server)

        IED.define_ied('Transmission.TIED2.Measurement', madlad.dict, 'tied2',
                       self.variables, self.server)

        # for key, val in madlad.dict.items():
        #     print(key)
        #     print(val)

        return self.variables


def main():
    serverClient = ServerClient('opc.tcp://0.0.0.0:4840')
    serverClient.connect()

    serverClient.update_client_object()
    serverClient.check_all_variable_consistency()
    serverClient.check_case_smart_home()
    serverClient.check_case_micro_grid()
    serverClient.check_case_generation()
    serverClient.check_case_tied1_tied2()
    serverClient.check_case_sied1_gied2()


if __name__ == "__main__":
    main()
