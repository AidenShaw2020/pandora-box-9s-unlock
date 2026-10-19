 SELECT                                                
     tbl_en.name                                       
   , tbl_game.game                                     
   , tbl_game.suffix                                   
   , tbl_en.idx                                        
   , tbl_class.name                                    
   , tbl_emu.name                                      
   , tbl_extra_info.name                               
   , tbl_game.max_life                                 
   , tbl_game.min_life                                 
   , tbl_game.difficulty                               
   , tbl_game.wait_time                                
   , tbl_game.charge_type                              
   , tbl_game.support_state                            
   , tbl_game.support_hd                               
   , tbl_game.arcade                                   
   , tbl_game.torrent                                  
 FROM                                                  
     tbl_en                                            
   , tbl_game                                          
   , tbl_class                                         
   , tbl_extra_info                                    
   , tbl_emu                                           
 WHERE                                                 
       tbl_game.id == tbl_en.id                        
   and tbl_game.game_type== tbl_class.class_id         
   and tbl_game.emu_type== tbl_emu.id                  
   and tbl_game.extra_info == tbl_extra_info.id        
