#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 23:42:02 2018

@author: villtord
"""

"""
This procedure is intended to convert data file *.sle measured in Specs Prodigy to HDF5 file.
IMPORTANT: IT works ONLY with COMPACT data!!!
"""
def SQL_converter_function(filename):
    
    import sqlite3
    import numpy as np
    from pandas.io import sql
    import struct
    import h5py
    from bs4 import BeautifulSoup
    from time import gmtime, strftime
    
    ####################################################################
    ####################### Create HDF5 file NEXUS #################
    ####################################################################
    
    fileNameHDF5 = filename.replace(".sle",".hdf5")
    
    f = h5py.File(fileNameHDF5, "w")
    
    timestamp=strftime("%Y-%m-%d %H:%M:%S", gmtime())
    
    f.attrs['default']          = 'entry'
    f.attrs['file_name']        = fileNameHDF5
    f.attrs['file_time']        = timestamp
    f.attrs['instrument']       = 'SPECS Prodigy'
    f.attrs['HDF5_Version']     = h5py.version.hdf5_version
    f.attrs['h5py_version']     = h5py.version.version
   
    ####################################################################
    ####################### Work with sqlite database #################
    ####################################################################
   
    cnx = sqlite3.connect(filename)
    
    raw_id      =   sql.read_sql ('''
                                  SELECT cast(RawID as integer) as raw_id
                                  FROM CountRateData;
                                  ''',
                                  cnx)
    
    schedule    =    sql.read_sql("""
                                  SELECT Value
                                  FROM Configuration
                                  WHERE Key = "Schedule";
                                  """,
                                  cnx)
    
    
    ####################################################################
    ####################### Work with schedule table - xml #############
    ####################################################################
    
    try:
        soup = BeautifulSoup(schedule.iloc[0,0],"xml")
    except:
        pass
    
    modes=[]
    modes_id=[]
    list_of_MCU_positions=[]
    
    try:
        spectrums_groups    =   soup.find_all ('SpectrumGroup')
    except:
        pass
    
    for j in spectrums_groups:
        modes.append(j.attrs['Name'])
        modes_id.append(j.attrs['ID'])
    
    try:
        MCU_positions  =   soup.find_all ('Range')
    except:
        pass
    
    
    for j in MCU_positions:
        axis_name = j.previous_sibling
        list_of_MCU_positions.append(axis_name.attrs['name'])
        list_of_MCU_positions.append(float(j.attrs['min']))
        list_of_MCU_positions.append(float(j.attrs['max']))
       
    
    
    write_trigger = False
    data_final  =   np.zeros(0)
    
    """ Iterate through all raws in CountRateData and combine them accordingly """
    
    for i in range(raw_id.shape[0]):
        
        """ Read region settings data from Spectrum table """
        
        node   = sql.read_sql("""
                              SELECT Node
                              FROM RawData
                              WHERE RawID = ?;
                              """,
                              cnx,params=[str(raw_id.iloc[i,0])])
    
        energy_channels = sql.read_sql ("""
                                  SELECT cast(EnergyChns as integer) as energy_channels
                                  FROM Spectrum WHERE Node = ?;
                                  """,
                                  cnx, params=[str(node.iloc[0,0])])
        
        non_energy_channels = sql.read_sql ("""
                                  SELECT cast(NonEnergyChns as integer) as non_energy_channels
                                  FROM Spectrum WHERE Node = ?;
                                  """,
                                  cnx, params=[str(node.iloc[0,0])])
    
        samples = sql.read_sql ("""
                                SELECT cast(Samples as integer) as samples
                                FROM Spectrum WHERE Node = ?;
                                """,
                                  cnx, params=[str(node.iloc[0,0])])
        
        """ Read actual data """
        
        data = sql.read_sql("""
                            SELECT Data 
                            FROM CountRateData 
                            WHERE rowid = ?;
                            """,
                            cnx, params=[str(i+1)])
    
        """ Unpack the byte array using type "d" to a numpy array/matrix """
    
        data_iter=struct.iter_unpack('d',data.iloc[0,0])
        
        data_array=list(data_iter)
    
        spectrum=np.array([i[0] for i in data_array])
       
        """ Check if Raw_ID is unique and Node is unique"""
        
        if (i != 0):                                        # if this is not the first frame
            
            if (raw_id.iloc[i,0] == raw_id.iloc[i-1,0]):    # if it is the same spectra separated due to length
                data_final=np.append(data_final,spectrum)   # append it to the previous spectrum
                data_2_hdf5 = data_final
            
            else:
                
                """ Now save the previous frame, but first check what was the previous node and other parameters """
                
                node_prev               =   sql.read_sql("""
                                                         SELECT Node
                                                         FROM RawData
                                                         WHERE RawID = ?;
                                                         """,
                                                         cnx,params=[str(raw_id.iloc[i-1,0])])
                
                energy_chns_prev        =   sql.read_sql("""
                                                        SELECT cast(EnergyChns as integer) as EnChn
                                                        FROM Spectrum
                                                        WHERE Node = ?;
                                                        """,
                                                        cnx,params=[str(node_prev.iloc[0,0])])
                
                non_energy_chns_prev    =   sql.read_sql("""
                                                        SELECT cast(NonEnergyChns as integer) as NEnChn
                                                        FROM Spectrum
                                                        WHERE Node = ?;
                                                        """,
                                                        cnx,params=[str(node_prev.iloc[0,0])])
                
                samples_prev            =   sql.read_sql("""
                                                        SELECT cast(Samples as integer) as Samples
                                                        FROM Spectrum
                                                        WHERE Node = ?;
                                                        """,
                                                        cnx,params=[str(node_prev.iloc[0,0])])
                
                """ Check if spectrum is actually 2D or 1D and reshape in case of 2D"""
                
                if (non_energy_chns_prev.iloc[0,0] != 1):
                    spectrum=spectrum.reshape(energy_chns_prev.iloc[0,0]*samples_prev.iloc[0,0], non_energy_chns_prev.iloc[0,0])
                
                """ If node was the same, then it is 2d/3D data """
                            
                if (node.iloc[0,0] == node_prev.iloc[0,0]):
                        data_final=np.dstack((data_final,spectrum))         # here we expand dimensions
                        data_2_hdf5 = data_final
                else:
                    data_final=spectrum
                    write_trigger = True
        
        else:
            
            if (non_energy_channels .iloc[0,0] != 1):
                spectrum=spectrum.reshape(energy_channels.iloc[0,0]*samples.iloc[0,0], non_energy_channels.iloc[0,0])
            data_final=spectrum
            data_2_hdf5 = data_final
            
        """ Here write the final matrix to a HDF5 file if next node is different """
        
        if write_trigger:
    
            nxgroup = f.create_group("Group "+modes[0])
            ds = nxgroup.create_dataset("Data "+str(i), data=data_2_hdf5)
            data_2_hdf5=data_final
            print ("write group "+str(i))
            
        write_trigger = False
     
    """ Do not forget to write the last spectrum from the loop """
    
    
    nxgroup = f.create_group("Group "+modes[0])
    ds = nxgroup.create_dataset("Data "+str(i+1), data=data_final)
    
    
    ########### Find scaling for data #########################
    
    try:
        result  =   soup.find('FixedAnalyzerTransmissionSettings')
        e_min   =   float(result.attrs['Ekin'])
        e_max   =   float(result.attrs['End'])
        e_delta =   float((e_max-e_min)/(float(result.attrs['NumValues'])-1))
        E_pass  =   int(result.attrs['Epass'])
        L_mode  =   str(result.attrs['LensMode'])
        N_scans =   int(result.attrs['NumScans'])
        scan_mode   =   'FAT'
    
    
    except:
        pass
    
    try:
        result  =   soup.find('SnapshotFATSettings')
        e_min   =   float(result.attrs['Ekin'])
        e_max   =   float(result.attrs['End'])
        e_delta =   float((e_max-e_min)/(float(result.attrs['NumValues'])-1))
        E_pass  =   int(result.attrs['Epass'])
        L_mode  =   str(result.attrs['LensMode'])
        N_scans =   int(result.attrs['NumScans'])
        scan_mode   =   'Snapshot'
    
    except:
        pass
    
    
    flag=True
    
    for i in range(len(list_of_MCU_positions)):
        try:
            if (list_of_MCU_positions[i] == 'tilt'):
                z_min=list_of_MCU_positions[i+1]
                z_max=list_of_MCU_positions[i+2]
                z_delta=float((z_max-z_min)/int((np.shape(data_final[1,1,:])[0])-1))
                flag=False
        except:
            pass
                
    if flag:
        z_min=list_of_MCU_positions[1]
        z_max=list_of_MCU_positions[2]
        z_delta=float((z_max-z_min)/int((np.shape(data_final[1,1,:])[0])-1))    
    
    Wave_Note=['Scan_Mode = '+scan_mode+', Lens_Mode = '+L_mode+', Pass_energy = '+str(E_pass)+' eV, Scans = '+str(N_scans)]
    Wave_Note_ascii = [n.encode("ascii", "ignore") for n in Wave_Note]
    ds.attrs['IGORWaveNote'] = Wave_Note_ascii
    
    if L_mode == "WideAngleMode":
        wide_angle = 12
    elif L_mode == "LowAngleMode":
        wide_angle = 7
        
    ds.attrs['IGORWaveScaling'] = [[0,0],[e_delta,e_min],[float(wide_angle/int(non_energy_channels.iloc[0,0])),-wide_angle/2],[z_delta,z_min]]
    
    f.close()