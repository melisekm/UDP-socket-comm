OR, XOR, AND = 1, 3, 4
pks_m_protocol = Proto("PKS_M",  "M Protocol")

type = ProtoField.uint8("PKS_M.type", "Typ", base.DEC)
fragment_id = ProtoField.uint32("PKS_M.fragment_id", "ID posielaneho fragmentu", base.DEC)
NACK = ProtoField.uint32("PKS_M.NACK", "Pocet a ID ziadanych packetov", base.dec)
NACK_IDS = ProtoField.string("PKS_M.nack_ids", "NACK IDS")
NACK_COUNT = ProtoField.uint32("PKS_M.NACK_COUNT", "Pocet ziadanych packetov", base.dec)
pocet_fragmentov = ProtoField.uint32("PKS_M.pocet_fragmentov", "Celkovy pocet fragmentov", base.DEC)
crc_chksum = ProtoField.uint16("PKS_M.crc_chksum", "CRC", base.HEX)
payload = ProtoField.string("PKS_M.payload", "Data Payload")


pks_m_protocol.fields = {type, fragment_id, NACK, NACK_IDS, NACK_COUNT, pocet_fragmentov, crc_chksum, payload}

function pks_m_protocol.dissector(buffer, pinfo, tree)
  length = buffer:len()
  if length == 0 then return end

  pinfo.cols.protocol = pks_m_protocol.name

  local subtree = tree:add(pks_m_protocol, buffer(), "PKS_M Data")

  local types = buffer(0,1):le_uint()
  local type_name = get_type_name(types)
  subtree:add_le(type,buffer(0,1)):append_text(" (" .. type_name .. ")")
  pinfo.cols.info:append(" Type: " .. type_name)
  
  if type_name == "INIT,DM" or type_name == "INIT,DF" then
    subtree:add_le(pocet_fragmentov,buffer(1,4))
  end

  if type_name == "DM" or type_name == "DF" then
    local f_id = buffer(1,4):le_uint()
    subtree:add_le(fragment_id, buffer(1,4))
    subtree:add_le(payload, buffer(5,length-7) ,"(" .. length-7 .. " bytes)")
    pinfo.cols.info:append(" ID: " .. f_id)
  end

  if type_name == "NACK" then
    local nack_ids = buffer(5,length-7):string()
    subtree:add_le(NACK_COUNT, buffer(1,4))
    subtree:add(NACK_IDS, buffer(5,length-7))
    pinfo.cols.info:append(" - " .. nack_ids)
  end

  local crc = buffer(length-2,2):le_uint()
  if crc == 0 then
    subtree:add_le(crc_chksum,buffer(length-2,2)):append_text(" (" .. "CORRUPTED" .. ")")
  else
    subtree:add_le(crc_chksum, buffer(length-2,2))
  end
  
end

function get_type_name(type)
  local res = "Unknown"

      if type ==   1 then res = "SYN"
  elseif type ==   2 then res = "ACK"
  elseif type ==   3 then res = "SYN,ACK" 
  elseif type ==   4 then res = "NACK"
  elseif type ==   8 then res = "INIT"
  elseif type ==  16 then res = "DM"
  elseif type ==  24 then res = "INIT,DM"
  elseif type ==  32 then res = "DF"
  elseif type ==  40 then res = "INIT,DF"
  elseif type ==  64 then res = "FIN"
  elseif type == 128 then res = "KA" end

  return res
end

local udp_port = DissectorTable.get("udp.port")
udp_port:add(5015, pks_m_protocol)