#!/usr/bin/env python
#!C:/python27/python.exe

# a thing to stuff arbitrary data into a png file!

import argparse
import os
import random
import re
import struct
import sys
import zlib

KEYS = [31, 47, 55, 59, 61, 62, 63, 79, 87, 91, 93, 94, 95, 
        103, 107, 109, 110, 111, 115, 117, 118, 119, 121, 122, 
        123, 124, 125, 126, 127, 143, 151, 155, 157, 158, 159, 
        167, 171, 173, 174, 175, 179, 181, 182, 183, 185, 186, 
        187, 188, 189, 190, 191, 199, 203, 205, 206, 207, 211, 
        213, 214, 215, 217, 218, 219, 220, 221, 222, 223, 227, 
        229, 230, 231, 233, 234, 235, 236, 237, 238, 239, 241, 
        242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 
        253, 254, 255]

class PNGSection:
   def __init__(self, length=0, chunktype='NONE', data=None, crc=0xFFFFFFFF):
      self.length = length
      self.type = chunktype
      self.data = data
      self.crc = crc

      if self.length == 0 and not data == None:
         self.length = len(data)

   def __str__(self):
      data = struct.pack('>L', self.length)
      data += self.type

      if self.data:
         data += self.data

      data += struct.pack('>L', self.crc)
      return data

   def __repr__(self):
      return '<PNGSection(type:%s / length:%d bytes / crc:0x%08X)>' % (self.type, self.length, self.crc)

class TextSection(PNGSection):
   def __init__(self, keyword, text):
      self.keyword = keyword
      self.text = text

      raw_data = self.make_data()
      PNGSection.__init__(self, len(raw_data), 'tEXt', raw_data)

   def make_data(self):
      return '%s\x00%s' % (self.keyword, self.text)

   @classmethod
   def from_png_data(cls, data):
      return cls(*data.split('\x00', 1))

class PNGFile:
   def __init__(self):
      self._sections = list()

   def append_section(self, length, chunktype, data, crc):
      self._sections.append(PNGSection(length, chunktype, data, crc))

   def insert_section(self, section, offset=-1):
      self._sections.insert(offset, section)

   def write(self, filename):
      fp = open(filename, 'wb')
      fp.write(str(self))
      fp.close()

   def __str__(self):
      data = struct.pack('>Q', 0x89504e470d0a1a0a)
      data += ''.join(map(str, self._sections))

      return data

   @classmethod
   def parse_from_data(cls, data):
      magic = struct.unpack('>Q', data[:8])[0]

      if not magic == 0x89504e470d0a1a0a:
         raise Exception('magic number is wrong! got 0x%08x' % magic)

      png_file = cls()
      png_data = data[8:]

      while png_data:
         length = struct.unpack('>L', png_data[:4])[0]
         chunktype = ''.join(struct.unpack('cccc', png_data[4:8]))
         png_data = png_data[8:]
         
         data = png_data[:length]
         crc = struct.unpack('>L', png_data[length:length+4])[0]
         png_data = png_data[length+4:]

         png_file.append_section(length, chunktype, data, crc)

      return png_file

   @classmethod
   def parse_from_file(self, filename):
      fp = open(filename, 'rb')
      data = fp.read()
      fp.close() 

      return PNGFile.parse_from_data(data)

   def __repr__(self):
      return '<PNGFile:(%s)>' % ', '.join(map(repr, self._sections))

def strxor(s, k):
   return ''.join(map(chr, map(lambda x: ord(x) ^ k, s)))

def get_data(filename):
   pngfile = PNGFile.parse_from_file(filename)

   text_sections = filter(lambda x: x.type == 'tEXt', pngfile._sections)

   if not len(text_sections):
      print 'no text section in image-- no data to pull out'
      sys.exit(1)

   got_panger = 0

   for section in text_sections:
      section = TextSection.from_png_data(section.data)

      for key in KEYS:
         header = strxor(section.keyword, key)

         if header[:7] == 'PANGER!':
            got_panger = 1
            break

      if got_panger:
         break

   if not got_panger:
      print 'no panger header'
      sys.exit(1)

   output_filename = header.split('!', 1)[1]
   output_data = zlib.decompress(strxor(section.text, key))

   fp = open(output_filename, 'wb')
   fp.write(output_data)
   fp.close()

def put_data(source_filename, dest_filename, output_filename):
   if not output_filename:
      output_filename = source_filename

   pngfile = PNGFile.parse_from_file(source_filename)

   fp = open(dest_filename, 'rb')
   dest_data = fp.read()
   fp.close()

   original_fn = re.split(r'\\|/', dest_filename)[-1]

   key = random.choice(KEYS)
   header = strxor('PANGER!%s' % original_fn, key)

   while '\x00' in header:
      key = random.choice(KEYS)
      header = strxor('PANGER!%s' % original_fn, key)

   enc_data = strxor(zlib.compress(dest_data,9), key)
   pngfile.insert_section(TextSection(header, enc_data))
   pngfile.write(output_filename)

if __name__ == '__main__':
   parser = argparse.ArgumentParser(description='Shove a file into or recover a file from a PNG image.')
   parser.add_argument('-i', '--image', help='the image to stick data in or get data from.', required=True)
   parser.add_argument('-g', '--get', help='get data from image.', action='store_true')
   parser.add_argument('-p', '--put', help='put data in an image.', action='store_true')
   parser.add_argument('-o', '--output', help='the name of the output image. if not present, the source image is overwritten.', default=None)
   parser.add_argument('-d', '--data', help='the filename of the data to put in the image.')
   args = parser.parse_args()

   if args.get:
      get_data(args.image)
   elif args.put:
      put_data(args.image, args.data, args.output)
   else:
      parser.print_usage()
      parser.exit(1, 'argument -g/--get or -p/--put is required')
