import datetime
import random
import math
import numpy as np

class TimestampedClass:
    def __init__(self, timestamp, value):
        self.timestamp = timestamp
        self.value = value
        self.avg_bw_last_t_window = None
        self.avg_len_last_t_window = None
        self.count_last_t = None
        self.ewma = None  #average packet size
        self.ewma_rate = None

    def get_timestamp(self):
        return self.timestamp

    def get_value(self):
        return self.value

    def set_avg_bw_last_t_window(self, avg):
        self.avg_bw_last_t_window = avg

    def get_avg_bw_last_t_window(self):
        return self.avg_bw_last_t_window

    def set_avg_len_last_t_window(self, avg_len):
        self.avg_len_last_t_window = avg_len

    def get_avg_len_last_t_window(self):
        return self.avg_len_last_t_window

    def set_ewma(self, ewma):
        self.ewma = ewma

    def get_ewma(self):
        return self.ewma

    def set_ewma_rate(self, ewma_rate):
        self.ewma_rate = ewma_rate

    def get_ewma_rate(self):
        return self.ewma_rate

    def set_count_last_t(self, count_last_t):
        self.count_last_t = count_last_t

    def get_count_last_t(self):
        return self.count_last_t



class TimestampedList:
    def __init__(self):
        self.timestamped_list = []
        self.bytes_in_window = 0
        self.pkt_in_window = 0

    def get_element (self, index) :
        return self.timestamped_list[index]

    def process_next(self,i,tau) :
        """
        evaluate the exact window based features for a single packet
        """
        obj = self.timestamped_list[i]
        value = obj.get_value()
        timestamp = obj.get_timestamp()
        self.bytes_in_window += value
        # delta = timestamp - self.timestamped_list[0].get_timestamp()
        # boolean = delta > 4131 and delta < 4133
        if  value > 0 :
            self.pkt_in_window += 1
            decrease = TimestampedClass (timestamp+tau,-value)
            self.insert(decrease,start_from=i)
        else :
            self.pkt_in_window -= 1
        obj.set_avg_bw_last_t_window((float(self.bytes_in_window))/tau)
        obj.set_count_last_t(self.pkt_in_window)
        if self.pkt_in_window > 0 :
            obj.set_avg_len_last_t_window((float(self.bytes_in_window))/self.pkt_in_window)
        else :
            obj.set_avg_len_last_t_window = 0
        # if boolean : print (tau, delta, value, self.pkt_in_window )
        
    def process_all (self, window) :
        i = 0
        while (i < len(self.timestamped_list)) :
            self.process_next(i, window) 
            i += 1 

    def insert(self, obj, start_from=0):
        for i in range(start_from,len(self.timestamped_list)):
            if obj.get_timestamp() <= self.timestamped_list[i].get_timestamp():
                self.timestamped_list.insert(i, obj)
                break
        else:
            self.timestamped_list.append(obj)

    def insert_random(self, n, T):
        current_time = datetime.datetime.now()

        for _ in range(n):
            timestamp_diff = datetime.timedelta(microseconds=random.uniform(0, T))
            timestamp = current_time - timestamp_diff  # Reverse the order to evaluate previous T microseconds
            value = random.randint(1, 100)
            obj = TimestampedClass(timestamp, value)
            self.insert(obj)

    def append(self, obj):
        self.timestamped_list.append(obj)

    def print_sorted_list(self, range = []):
        for obj in self.timestamped_list:
            print(f"Tstamp: {obj.get_timestamp()}, Val: {obj.get_value()}, Avg T Win: {obj.get_avg_bw_last_t_window()}, EWMA: {obj.get_ewma()}")

    def get_time_values(self, times=[], count=[], avg_len=[], bw=[]):
        """
        extract the timestamps and the values of avg bw, count, avg len
        """
        for obj in self.timestamped_list:
            
            # timestamp = obj.get_timestamp()
            # delta = timestamp - self.timestamped_list[0].get_timestamp()
            # boolean = delta > 4131 and delta < 4133
            # if boolean : print ( delta, obj.get_count_last_t() )

            times.append (obj.get_timestamp())
            bw.append (obj.get_avg_bw_last_t_window())
            avg_len.append (obj.get_avg_len_last_t_window())
            count.append (obj.get_count_last_t())

    # def evaluate_average_previous_T(self, T):
    #     for i in range(len(self.timestamped_list)):
    #         current_time = self.timestamped_list[i].get_timestamp()
    #         start_time = current_time - datetime.timedelta(microseconds=T)

    #         total_value = 0
    #         count = 0

    #         for j in range(i, -1, -1):
    #             obj = self.timestamped_list[j]

    #             if obj.get_timestamp() >= start_time:
    #                 total_value += obj.get_value()
    #                 count += 1
    #             else:
    #                 break

    #         if count > 0:
    #             average = total_value / count
    #             self.timestamped_list[i].set_avg_last_t_window(average)
    #         else:
    #             self.timestamped_list[i].set_avg_last_t_window(0)  # Set average to 0 if no elements within the specified time range

    def evaluate_ewma(self, tau, times = [], ewma_values=[], ewma_rate_values=[] ):
        if not self.timestamped_list:
            return

        self.timestamped_list[0].set_ewma(self.timestamped_list[0].get_value())
        self.timestamped_list[0].set_ewma_rate(1)
        times.append(self.timestamped_list[0].get_timestamp())
        ewma_values.append (self.timestamped_list[0].get_value())
        ewma_rate_values.append (1)

        for i in range(1, len(self.timestamped_list)):
            value = self.timestamped_list[i].get_value()
            time = self.timestamped_list[i].get_timestamp()
            prev_ewma = self.timestamped_list[i - 1].get_ewma()
            prev_ewma_rate = self.timestamped_list[i - 1].get_ewma_rate()
            prev_time = self.timestamped_list[i - 1].get_timestamp()
            decay = math.exp(-(time-prev_time)/tau)
            # ewma =  value/tau * (1-decay) + prev_ewma * decay
            ewma =  value * (1-decay) + prev_ewma * decay
            ewma_rate =  1 + prev_ewma_rate * decay
            # if i >= 1700 and i <= 1703 :
            #     print(i,decay, prev_ewma_rate, ewma_rate)

            self.timestamped_list[i].set_ewma(ewma)
            self.timestamped_list[i].set_ewma_rate(ewma_rate)
            times.append(time)
            ewma_values.append (ewma)
            ewma_rate_values.append (ewma_rate)
    
    def sample_and_hold(self,times = [], count=[], avg_len=[], bw=[] ) :
        i = 0 
        while (i < len(times)-1) :
            next_time = times[i+1]
            times.insert(i+1,next_time)
            count.insert(i+1,count[i])
            avg_len.insert(i+1,avg_len[i])
            bw.insert(i+1,bw[i])
            i += 2

    def time_slice(self, times = [], values = [], start_time=0.0, end_time=np.inf,
                   duration = np.inf, samples = np.inf) :
        out_times = []
        out_values = []
        if duration < np.inf :
            end_time = min(end_time,start_time+duration)
            print (end_time)
        counter = 0
        for i in range(len(times)) :
            timestamp = times [i]
            # print (timestamp)
            if timestamp > end_time : 
                # print ('end_time')
                break
            if timestamp >= start_time :
                out_times.append(timestamp)
                out_values.append(values[i])
                counter +=1 
            if counter >= samples : 
                # print ('samples')
                break
        # print (out_times, out_values)
        return out_times, out_values


# Example usage
# timestamped_list = TimestampedList()

# # Insert 5 instances with random timestamps
# timestamped_list.insert_random(5, 500000)  # T = 500000 microseconds

# # Evaluate average value over the previous 300000 microseconds for each element
# timestamped_list.evaluate_average_previous_T(300000)

# # Evaluate EWMA with alpha = 0.5
# timestamped_list.evaluate_ewma(0.5)

# # Print the sorted list with evaluated averages and EWMA
# timestamped_list.print_sorted_list()
