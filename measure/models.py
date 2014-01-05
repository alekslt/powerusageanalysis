
import MySQLdb
import functools

from .config import (
    db,
    )

def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


class Consumer(object):
	def __init__(self, start, wattUsage):
		self.start = start
		self.wattUsage = wattUsage
		pass

	def toDict(self):
		return { 'start' : self.start, 'stop': 0, 'watt': self.wattUsage}

class Measurements(object):
	def __init__(self, x):
		self.logbuffer = []
		self.consumers = []
		self.values = []

		self.x = x
		self.wattmargin = 29
		self.samples = 9
		
		self.startDate = "2013-11-15 00:45:00"
		self.endDate = "2013-11-15 09:30:00"

		self.log("", "Measurements from " + self.startDate + " to " + self.endDate)
		self.log("", "Watt tolerancemargin " + str(self.wattmargin))
		self.log("", "Watt averaging sample count " + str(self.samples))

		# you must create a Cursor object. It will let
		#  you execute all the query you need
		cur = db.cursor() 

		# Use all the SQL you like
		cur.execute("SELECT UNIX_TIMESTAMP(time) as epochtime,data FROM measure_watt where time > '" + self.startDate + "' and time < '" + self.endDate + "'")

		# print all the first cell of all the rows
		for row in cur.fetchall() :
			self.values.append( { 'x': int(row[0]), 'y' : row[1], 'info' : {} } )
			self.x = row[0]

		self.log("", "Total sample count " + str(len(self.values)) )
		self.analyze()

	def log(self, time, message, level = 0):
		outmesg = str(time) + " | " + " " * level + str(message)
		print outmesg
		self.logbuffer.append(outmesg)

	def getConsumer(self, wattUsage):
		for cons in self.consumers:
			if cons.wattUsage >= wattUsage-self.wattmargin and cons.wattUsage <= wattUsage+self.wattmargin:
				return cons

		return None

	def addConsumer(self, start, wattUsage):
		cons = Consumer(start, wattUsage)
		self.consumers.append(cons)
		return cons

	def getOrCreateConsumer(self, start, wattUsage):
		cons = self.getConsumer(wattUsage)
		if cons is None:
			cons = self.addConsumer(start, wattUsage)

		self.log(start, "Adding Consumer using " + str(wattUsage) + " watts",2)
		return cons

	def subsetsum(self, items, maxweight):
		@memoize
		def f(v, i, S):
			if i >= len(v): return 1 if (S >= (-1*self.wattmargin) and S <= self.wattmargin) else 0

			count = f(v, i + 1, S)
			count += f(v, i + 1, S - v[i].wattUsage)
			return count     # <-- Return memoized value.

		tempWeight = maxweight
		subset = []
		for i, item in enumerate(items):
			# Check if there is still a solution if we include items[i]
			#print "  ## Checking item: " + str(item.wattUsage)
			if f(items, i + 1, tempWeight - item.wattUsage) > 0:
				subset.append(item)
				tempWeight -= item.wattUsage

		return subset

	def removeConsumer(self, wattUsage):
		self.consumers[:] = [x for x in self.consumers if not (x.wattUsage >= wattUsage-self.wattmargin and x.wattUsage <= wattUsage+self.wattmargin)]

	def removeConsumers(self, time, wattUsage):
		matchedConsumers = self.subsetsum(self.consumers, wattUsage)

		if len(matchedConsumers) == 0:
			self.log(time, "Trying to remove consumers using: " + str(wattUsage) + " but none found!!", 2)
		#directMatch = [x for x in self.consumers if (x.wattUsage >= wattUsage-self.wattmargin and x.wattUsage <= wattUsage+self.wattmargin)]
		for cons in matchedConsumers:
			self.consumers.remove(cons)
			self.log(time, "Removed consumer using " + str(cons.wattUsage) + " watts",2)


	def getConsumers(self):
		out = ""
		for cons in self.consumers:
			out += "Consumer Started: " + str(cons['start']) + ", Using: " + str(cons['watt']) + "\n"

		return out

	def analyze(self):
		consumers = []
		runningAvgValue = 0
		avgWatt = 0
		avgDiff = 0
		avgValues = -1
		avgStartWatt = self.values[0]['y']
		matchStartTime = 0

		for point in self.values:
			#print "Checking: " + point['x'] + "\n"
			#diff = point['y'] - lastUsage
			runningAvgValue += point['y']
			runningAvgValue /= 2
			#point['y'] = runningAvgValue

			avgStartDiff = point['y'] - avgStartWatt

			if avgValues == -1 and abs(avgStartDiff) > self.wattmargin:
				avgValues = self.samples
				avgWatt = point['y']
				avgDiff = avgStartDiff
				matchStartTime = point['x']

				self.log(matchStartTime, "Possible consumer change with diff: " + str(avgDiff) + " watts. Starting averaging", 0)

			if avgValues > 0:
				avgValues -= 1

				avgWatt += point['y']
				avgWatt = avgWatt / 2

				avgDiff += avgStartDiff
				avgDiff = avgDiff / 2
			#else:
			#	avgStartWatt = point['y']

			if avgValues == 0:
				avgValues = -1
				avgStartWatt = avgWatt

				self.log(matchStartTime, "Consumer avgdiff " + str(avgDiff), 1)
				if abs(avgDiff) > self.wattmargin:
					if avgDiff > 0:
						cons = self.getOrCreateConsumer(matchStartTime, avgDiff)
						
					else:
						self.removeConsumers(matchStartTime, abs(avgDiff))
						

			point['info'] = [x.toDict() for x in self.consumers]
		pass

	def __json__(self, request):
		return {'wattdata': self.values, 'log': self.logbuffer}